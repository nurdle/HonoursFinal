import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash_html_components.Button import Button
from matplotlib.pyplot import text
import twitter, tweepy
import json
import os
import flask, io
from datetime import datetime, timedelta
import SentimentAnalysis
import plotly.express as px
import plotly.graph_objs as go
from dotenv import load_dotenv
load_dotenv()

key = os.environ.get("consumer_key")
secret = os.environ.get("consumer_secret")
access_key = os.environ.get("access_token_key")
access_secret = os.environ.get("access_token_secret")
print("Loaded imports...")

print("Loading stylesheets and initialising dashboard...")
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
print("Done!")

firstDate = 0
def list_duplicates_of(seq,item):
    start_at = -1
    locs = []
    while True:
        try:
            loc = seq.index(item,start_at+1)
        except ValueError:
            break
        else:
            locs.append(loc)
            start_at = loc
    return locs
api = twitter.api.Api(consumer_key = key,
                    consumer_secret = secret,
                    access_token_key= access_key,
                    access_token_secret= access_secret,
                    tweet_mode='extended')
auth = tweepy.OAuthHandler(key, secret)
auth.set_access_token(access_key, access_secret)
api = tweepy.API(auth)
app.layout = html.Div(children=[html.H1("Can an AI be applied to determine whether or not a twitter account is populist?"),
    html.Div(children='''
        Below, you will find a tool for entering a twitter account, selecting a date range, loading tweets, analysing them, and determining how "populist" that user appears to be
        You can copy the text in the data boxes for later use. You can also enter your own data if you want as long as it follows the same format as is usually used by the tool
        (Tweets need to be in the format: "TEXT:'[TWEET]'", analysed data should be in the format: '"[SUBJECT]": [VALUE]'). This tool uses the following definition for the term
        "Populism": "a populist will attempt to use policy or language that invokes the most amount of “common” people against either the elite or the perceived elite with a 
        particular focus on some form of crisis or perceived crisis."
    ''', style={"backgroundColor":"#a7acb5"}),
    
    html.P('''This tool will load a set of tweets from the account you enter, analyse the sentiment of each tweet, determine the subject of each tweet and measure this against a 
    defined list of populist opinions.
    The first step is to enter the account you wish to analyse, select a date range and press the "Find Tweets" button''', style={"backgroundColor":"#a7acb5"}),
    html.P('''WARNING: due to restrictions from the Twitter API only 900 tweets can be requested by this total every 15 minutes. Note, this is for the entire app, not each user.
    
    Generally, it is best to request a small batch of recent tweets. The output from the request will be shown in the text box below which can be copied and pasted for later user,
    same for the sentiment analysis ouput WARNING: This tool is currently designed for modern American politics so any queries from other countries or areas are likely to be innacurate. 
    If possible, please keep queries to within the United States''', style={"backgroundColor":"#ba908a"}),
    html.Div(["Twitter handle: @",
                dcc.Input(id="handle-input", value="atrupar", type='text')]),
    html.Div([dcc.RangeSlider(
        id="date-slider",
        min=0,
        max=1,
        step=1,
        value=[0,50],
        allowCross=False

    )]),
    html.Div(id="slider-label", children=""),
    html.Div(id="hidden-date-value", style={'display': 'none'}),
    html.Button("Find Tweets", id="submit-btn", n_clicks=0),
    dcc.Loading(
            id="loading-1",
            type="default",
            fullscreen = True,
            children = html.Div(["Found tweets: ",
                                    dcc.Textarea(id = "return-text", value="", style={'width':'100%'})]),
        ),
    html.P('''You should now have a block of text with the tweets requested. Now press the analyse button and you will see the extracted sentiments''', style={"backgroundColor":"#a7acb5"}),
    html.Button("run-analysis", id="analyse-button", n_clicks=0),
    dcc.Loading(
            id="loading-2",
            type="default",
            fullscreen = True,
            children = dcc.Textarea(id = "analysis-text", value="", style={'width':'100%'}),
        ),
    html.P('''You should now see a list of all the extracted sentiments. You can now press the "Create Graph" button below to see a graphical representation of these opinions
    and the final "populist score" for this account''', style={"backgroundColor":"#a7acb5"}),
    html.Button("Create Graph", id="graph-button", n_clicks=0),
    dcc.Graph(id="LeftPlot"),
    dcc.Graph(id="RightPlot"),
    html.Div(id="FinalScoreText", style={"backgroundColor":"#a7acb5"})
    ],
     style={'margin-left':'auto','width': "50%", 'margin-right':'auto', 'text-align':'center'},
    )

@app.callback(
    [Output("date-slider", "max"),
    Output("hidden-date-value", "children")],
    ##Output("slider-label", "children")
    [Input("handle-input", "value")]
)
def UpdateSlider(name):
    print(name)
    date = api.get_user(screen_name=name).created_at
    Max = datetime.today() - date
    date = date.date()
    print(Max)
    return Max.days, date

@app.callback(
    Output("slider-label", "children"),
    [Input("date-slider", "value")],
    [Input("hidden-date-value", "children")]
)
def UpdateSliderLabel(value, firstDate):
    firstDate = datetime.strptime(firstDate, '%Y-%m-%d')
    First = (firstDate + timedelta(days = value[0]))
    Second = (firstDate + timedelta(days = value[1]))
    return "First date: {} Second date: {}".format(First, Second)

@app.callback(
    Output("return-text", 'value'),
    [Input("submit-btn", "n_clicks")],
    [State("date-slider", "value")],
    [State("hidden-date-value", "children")],
    [State('handle-input', 'value')],
)
def GetTweets(n_clicks, dates,firstDate, name ):
    ##name = str(input("Please enter the name of the user: "))
    name = str(name)
    ##file = open(os.getcwd() + "/dash/download/Data.csv", "w")
    RetString = ""
    print("FIRST DATE: ", type(firstDate))
    firstDate = str(firstDate)
    print(firstDate)
    try:
        firstDate = datetime.strptime(firstDate, '%Y-%m-%d')
    except:
        return "Please load tweets from an account above, or copy pre-saved data here"
    startDate = (firstDate + timedelta(days = dates[0]))
    endDate = (firstDate + timedelta(days = dates[1]))
    First = startDate
    Second = endDate
    Count = (Second - First).days
    print((Second - First).days)
    tl = api.user_timeline(screen_name=name, include_rts=False, count = 100)
    tweets = []
    print("adding tweets to list...")
    for tweet in tl:
        if tweet.created_at < endDate and tweet.created_at > startDate:
            tweets.append(tweet)
    print(tweets)
    try:
        while (tl[-1].created_at > startDate):
            print("Last Tweet @", tl[-1].created_at, " - fetching some more")
            tl = api.user_timeline(name, max_id = tl[-1].id, count=100, include_rts=False)
            for tweet in tl:
                if tweet.created_at < endDate and tweet.created_at > startDate:
                    tweets.append(tweet)
        print(tl)
    except:
        print("Index limit reached...continuing...")
    ##RetString = []
    print("Encoding tweets...")
    for items in tweets:
        OutData = items.text
        OutData = str(OutData.encode("utf-8")) + "\n"
        OutData = OutData[1:]
        print(OutData)
        RetString += str(("TEXT: " + OutData)) 
    print("Done!")
    ##RetString.encode("utf-8")
    print(RetString)
    return RetString
@app.callback(
    Output("analysis-text", "value"),
    [Input("analyse-button", "n_clicks")],
    [State("return-text", "value")]
)
def analyse(foo, text):
    print("RUNNING ANALYSIS")
    tweets = text.split("TEXT: ")
    #print(tweets)
    Results = SentimentAnalysis.AnalyseTweets(tweets)
    #print(Results)
    print("Analysis complete")
    retString = json.dumps(Results)
    return retString

@app.callback(
    Output("LeftPlot", "figure"),
    Output("RightPlot", "figure"),
    Output("FinalScoreText", "children"),
    [Input("graph-button", "n_clicks")],
    State("analysis-text", "value")
)
def updateScatter(n_clicks, data):
    print(data)
    data = data[1:-1]
    items = data.split(',')
    namesList, valuesList = [],[]
    DDict = {}
    RightView, LeftView = 0.0, 0.0
    for i in items:
    #print(i)
        try:
            Value = float(i[-4:])
        except:
            continue
        Key = i[:-5]
        if "http" in Key:
            continue
        print("KEY: {} VALUE: {}".format(Key, Value))
        DDict[Key] = Value
    
    print(DDict)
    file = open("Opinions.csv", "r")
    Lefts, Rights, LNames, RNames = [], [], [], []
    for lines in file:
        try:
            Item, Left, Right = lines.split(",")
        except:
            continue
        print(Item)
        for keys in DDict.keys():
            if Item in keys:
                print("NAME FOUND: {}".format(Item))
                if int(Left) == 1:
                    print("APPENDING LEFT")
                    LLocations = list_duplicates_of(LNames, Item)
                    if len(LLocations) > 0:
                        Lefts[LLocations[0]] =+ DDict.get(keys)
                        continue
                    Lefts.append(DDict.get(keys))
                    LNames.append(Item)
                elif int(Right) == 1:
                    RLocations = list_duplicates_of(RNames, Item)
                    if len(RLocations) > 0:
                        Rights[RLocations[0]] =+ DDict.get(keys)
                        continue
                    Rights.append(DDict.get(keys))
                    RNames.append(Item)
    print("Lefts: {}, Rights: {}".format(Lefts, Rights))
    LDict = dict(names=LNames, values=Lefts)
    Leftfig = px.bar(LDict, x="names", y="values")
    RDict = dict(names=RNames, values=Rights)
    Rightfig = px.bar(RDict, x="names", y="values")
    
    for items in Lefts:
        LeftView += float(items)
    for items in Rights:
        RightView += float(items)
    if LeftView > RightView:
        RetString = "This account appears to share left-wing populist views with a score of {} (Right-Wing score was: {})".format(LeftView, RightView)
        if abs(LeftView - 0) <= 1:
            RetString += "\n However, it should be noted that the overall score was very low (~0) so this user is not likely to be a populist"
    elif RightView < LeftView:
        RetString = "This account appears to share right-wing populist views with a score of {} (Left-Wing score was: {})".format(RightView, LeftView)
        if abs(RightView - 0) <= 1:
            RetString += "\n However, it should be noted that the overall score was very low (~0) so this user is not likely to be a populist"
    else:
        RetString = "This account does not appear to share populist opinions with either wing (they may still be populist, but they do not share talking points with either wing)"
    return Leftfig, Rightfig, RetString

'''attempts = 0
while attempts < 11:
    try:
        app.run_server(debug=True)
    except:
        attempts += 1'''

if __name__ == '__main__':
	app.run_server(debug=True)
