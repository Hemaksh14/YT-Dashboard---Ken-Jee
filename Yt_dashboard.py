# -*- coding: utf-8 -*-
"""
Created on Sat Apr  9 15:18:13 2022

@author: Hemaksh
"""
#libraries used
import pandas as pd 
import numpy as np 
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from datetime import datetime


#Defining functions
#To map negative values
def style_negative(v, props=''):
    """ Style negative values in dataframe"""
    try: 
        return props if v < 0 else None
    except:
        pass

#To map positive values    
def style_positive(v, props=''):
    """Style positive values in dataframe"""
    try: 
        return props if v > 0 else None
    except:
        pass  

#indicates the country
def audience_simple(country):
    """Show top represented countries"""
    if country == 'US':
        return 'USA'
    elif country == 'IN':
        return 'India'
    else:
        return 'Other'

#loading data with basic feature engineering
#streamlit has a system in place where you can cache the data instead of having to reload it again and again
@st.cache 
def load_data():
    #iloc used to remove Column-'Total'
    df_agg = pd.read_csv('Aggregated_Metrics_By_Video.csv').iloc[1:,:]
    #renaming columns
    df_agg.columns = ['Video','Video title','Video publish time','Comments added','Shares','Dislikes','Likes',
                          'Subscribers lost','Subscribers gained','RPM(USD)','CPM(USD)','Average % viewed','Average view duration',
                          'Views','Watch time (hours)','Subscribers','Your estimated revenue (USD)','Impressions','Impressions ctr(%)']
    #changing the 'Video publish time' from string to datetime datatype
    df_agg['Video publish time'] = pd.to_datetime(df_agg['Video publish time'])
    #changing the 'Average view duration' from string to datetime but also splitting them to hours min and seconds
    df_agg['Average view duration'] = df_agg['Average view duration'].apply(lambda x: datetime.strptime(x,'%H:%M:%S'))
    df_agg['Avg_duration_sec'] = df_agg['Average view duration'].apply(lambda x: x.second + x.minute*60 + x.hour*3600)
    #created 2 new metrics to -'Engagement ratio' is all engagement divided by views and another metric which is 'views/subs gained'
    df_agg['Engagement_ratio'] =  (df_agg['Comments added'] + df_agg['Shares'] +df_agg['Dislikes'] + df_agg['Likes']) /df_agg.Views
    df_agg['Views / sub gained'] = df_agg['Views'] / df_agg['Subscribers gained']
    df_agg.sort_values('Video publish time', ascending = False, inplace = True)
    
    df_agg_sub = pd.read_csv('Aggregated_Metrics_By_Country_And_Subscriber_Status.csv')
    df_comments = pd.read_csv('Aggregated_Metrics_By_Video.csv')
    df_time = pd.read_csv('Video_Performance_Over_Time.csv')
    #changing the 'Date' in dataframe time from string to datetime datatype
    df_time['Date'] = pd.to_datetime(df_time['Date'])
    return df_agg, df_agg_sub, df_comments, df_time 

#create dataframes from the function 
df_agg, df_agg_sub, df_comments, df_time = load_data()


#additional data engineering for aggregated data 
#creating a copy of aggregated data is a good practice so that you dont mess up the orignal dataframe
df_agg_diff = df_agg.copy()
#max is used to get the latest video and then we take one year off of it to get a 1 year time window for relevance
metric_date_12mo = df_agg_diff['Video publish time'].max() - pd.DateOffset(months =12)
#getting median of each column in the 1 year time window 
median_agg = df_agg_diff[df_agg_diff['Video publish time'] >= metric_date_12mo].median()


#create differences from the median for values 
#Just numeric columns 
numeric_cols = np.array((df_agg_diff.dtypes == 'float64') | (df_agg_diff.dtypes == 'int64'))
df_agg_diff.iloc[:,numeric_cols] = (df_agg_diff.iloc[:,numeric_cols] - median_agg).div(median_agg)

#merge daily data with publish data to get delta 
df_time_diff = pd.merge(df_time, df_agg.loc[:,['Video','Video publish time']], left_on ='External Video ID', right_on = 'Video')
df_time_diff['days_published'] = (df_time_diff['Date'] - df_time_diff['Video publish time']).dt.days

# get last 12 months of data rather than all data 
date_12mo = df_agg['Video publish time'].max() - pd.DateOffset(months =12)
df_time_diff_yr = df_time_diff[df_time_diff['Video publish time'] >= date_12mo]

# get daily view data (first 30), median & percentiles 
views_days = pd.pivot_table(df_time_diff_yr,index= 'days_published',values ='Views', aggfunc = [np.mean,np.median,lambda x: np.percentile(x, 80),lambda x: np.percentile(x, 20)]).reset_index()
views_days.columns = ['days_published','mean_views','median_views','80pct_views','20pct_views']
views_days = views_days[views_days['days_published'].between(0,30)]
views_cumulative = views_days.loc[:,['days_published','median_views','80pct_views','20pct_views']] 
views_cumulative.loc[:,['median_views','80pct_views','20pct_views']] = views_cumulative.loc[:,['median_views','80pct_views','20pct_views']].cumsum()


########################
#Streamlit begins
########################

#building the dashboard
add_sidebar = st.sidebar.selectbox('Aggregate or Individual Video', ('Aggregate Metrics','Individual Video Analysis'))

#Show individual metrics 
#Aggregate Metric
if add_sidebar == 'Aggregate Metrics':
    st.header("Ken Jee YouTube Aggregated Data")
    
    df_agg_metrics = df_agg[['Video publish time','Views','Likes','Subscribers','Shares','Comments added','RPM(USD)','Average % viewed',
                             'Avg_duration_sec', 'Engagement_ratio','Views / sub gained']]
    #getting a 6 month window from latest video
    metric_date_6mo = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months =6)
    #getting a 12 month window from latest video
    metric_date_12mo = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months =12)
    metric_medians6mo = df_agg_metrics[df_agg_metrics['Video publish time'] >= metric_date_6mo].median()
    metric_medians12mo = df_agg_metrics[df_agg_metrics['Video publish time'] >= metric_date_12mo].median()
    
    #creating 5 columns
    col1, col2, col3, col4, col5 = st.columns(5)
    columns = [col1, col2, col3, col4, col5]
    
    #runing for loop to display the metrics in columns
    count = 0
    for i in metric_medians6mo.index:
        with columns[count]:
            delta = (metric_medians6mo[i] - metric_medians12mo[i])/metric_medians12mo[i]
            st.metric(label= i, value = round(metric_medians6mo[i],1), delta = "{:.2%}".format(delta))
            count += 1
            if count >= 5:
                count = 0
    
    #get date information and remove timestamp 
    df_agg_diff['Publish_date'] = df_agg_diff['Video publish time'].apply(lambda x: x.date())
    df_agg_diff_final = df_agg_diff.loc[:,['Video title','Publish_date','Views','Likes','Subscribers','Shares','Comments added','RPM(USD)','Average % viewed',
                             'Avg_duration_sec', 'Engagement_ratio','Views / sub gained']]

    #getting a list of all numeric columns in the dataframe
    df_agg_numeric_lst = df_agg_diff_final.median().index.tolist()
    #changing values from decimals to percentage values
    df_to_pct = {}
    for i in df_agg_numeric_lst:
        df_to_pct[i] = '{:.1%}'.format
    
    #showing dataframe/table with colour mapping
    st.dataframe(df_agg_diff_final.style.hide().applymap(style_negative, props='color:red;').applymap(style_positive, props='color:green;').format(df_to_pct))

    #top videos with highest engagement ratio
    input_column,pie_chart_col = st.columns([1,2])
    
    top_videos = df_agg[['Video title', 'Engagement_ratio']]
    top_v= top_videos.sort_values('Engagement_ratio', ascending= False)
    
    top_n = input_column.text_input('How many of the top videos would you like to see?', 5)
    top_n = int(top_n)
    top_v = top_v.head(top_n)
    
    fig = px.pie(top_v, values='Engagement_ratio', names='Video title')
    pie_chart_col.write(fig)

#Individual video analysis 
if add_sidebar == 'Individual Video Analysis':
    videos = tuple(df_agg['Video title'])
    st.write("Individual Video Performance")
    video_select = st.selectbox('Pick a Video:', videos)
    
    agg_filtered = df_agg[df_agg['Video title'] == video_select]
    agg_sub_filtered = df_agg_sub[df_agg_sub['Video Title'] == video_select]
    agg_sub_filtered['Country'] = agg_sub_filtered['Country Code'].apply(audience_simple)
    agg_sub_filtered.sort_values('Is Subscribed', inplace= True) 
    
    #making a 'Country' filtered subscription plot
    fig = px.bar(agg_sub_filtered, x ='Views', y='Is Subscribed', color ='Country', orientation ='h')
    #passing the figure to streamlit 
    st.plotly_chart(fig)
    
    agg_time_filtered = df_time_diff[df_time_diff['Video Title'] == video_select]
    first_30 = agg_time_filtered[agg_time_filtered['days_published'].between(0,30)]
    first_30 = first_30.sort_values('days_published')
   
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['20pct_views'],
                    mode='lines',
                    name='20th percentile', line=dict(color='green', dash ='dash')))
    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['median_views'],
                        mode='lines',
                        name='50th percentile', line=dict(color='yellow', dash ='dash')))
    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['80pct_views'],
                        mode='lines', 
                        name='80th percentile', line=dict(color='white', dash ='dash')))
    fig2.add_trace(go.Scatter(x=first_30['days_published'], y=first_30['Views'].cumsum(),
                        mode='lines', 
                        name='Current Video' ,line=dict(color='firebrick',width=8)))
        
    fig2.update_layout(title='View comparison first 30 days',
                   xaxis_title='Days Since Published',
                   yaxis_title='Cumulative views')
    
    st.plotly_chart(fig2)
    
    

    