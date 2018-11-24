from pymongo import MongoClient
from flask import(Flask, render_template, jsonify)
from .Data.CountySelection import CountySelection
from .Data.convertXlsToJSON import CreateMongoDataBase
from .Data.Mongodbset import mongodbset
import win32com.client as wc
import pythoncom
#------------------------------------------------------------------------------------#
# Flask Setup #
#------------------------------------------------------------------------------------#

app = Flask(__name__, template_folder='templates') 

#------------------------------------------------------------------------------------#
# Local MongoDB connection #
#------------------------------------------------------------------------------------#
conn = "mongodb://localhost:27017" 
client = MongoClient(conn)
# create / Use database
db = client.healthi_db
#------------------------------------------------------------------------------------#
# MLab MongoDB connection #
#------------------------------------------------------------------------------------#
# #### Connection for remote host
# conn = 'mongodb://<dbuser>:<dbpassword>@ds255332.mlab.com:55332/healthi_db'

# client = MongoClient(conn,ConnectTimeoutMS=30000)
# db = client.get_default_database()
# #------------------------------------------------------------------------------------#
#### Initialise and populate the Collection / Database
#------------------------------------------------------------------------------------#
def InitializeDataBase():
    CreateMongoDataBase()
    mongodbset()

#------------------------------------------------------------------------------------#
# Home Page
@app.route("/")
def home():
    return(render_template("Landing.html"))

# Route to display all the five attributes to measure health of a county
@app.route("/routes")
def routes():
    sample_list = []
    Routes_dict = {}
    Routes_dict['Attributes'] = "/attributes"
    Routes_dict['States']= "/states"
    Routes_dict['State County Names']="/countynames/<state>"
    Routes_dict['State Zscores Countywise'] ="/countyzscores/<state>"
    Routes_dict['State Details Countywise']="/countyalldetails/<state>"
    Routes_dict['State Geographical & Demographical Details Countywise'] = "/countygeodetails/<state>"
    Routes_dict['Ranks & Zscores Details Countywise'] = "/countyrankszscores/<state>"
    Routes_dict['User Selection'] = "/attributeSelection/<userSelection>"
    
    sample_list.append(Routes_dict)
    return jsonify(sample_list)

# Route to display all the five attributes to measure health of a county
@app.route("/attributes")
def attributes(): 
    sample_list = []
    for item in db.Category.find():
        for cat in item['cat']:
            sample_list.append(cat)
    return jsonify(sample_list)

# Route to display all the ranks to measure health of a county
@app.route("/countyrankszscores/<state>")
def rankszscores(state):
    sample_list = []
    County_dict = {}
    for item in db.CountyRanksZscores.find({'State': state}):
        County_dict[state.upper()] = item['CountyDetails']
    sample_list.append(County_dict)    
    return jsonify(sample_list)    

#Route to display all the states present in the database
@app.route("/states")
def state():
    sample_list = []
    states_list = []
    Statedict={}
    for item in db.State.find():
        states_list.append(item['StateName'])
        
    Statedict['States'] = states_list 
    sample_list.append(Statedict)
    return jsonify(sample_list)  

#Route to display the county names of all the counties present in the given state
@app.route("/countynames/<state>")
def county(state):
    sample_list = []
    for item in db.State.find({'StateName': state}):
        county_list=[]
        County_dict={}
        State_Counties = item['Counties']
        for County in State_Counties:
            county_list.append(County['County']['CountyName'])
            County_dict['CountyNames'] = county_list          
            sample_list.append(County_dict)
    return jsonify(sample_list)   

#Route to display all the zscores and rank of all the counties for the given state
@app.route("/countyzscores/<state>")
def zscore(state):
    sample_list = []
    for item in db.State.find({'StateName': state}):
        State_Counties = item['Counties']
        for Zscores in State_Counties:              
            sample_list.append({Zscores['County']['CountyName']:{
            "QualityofLife":Zscores['County']['QualityofLife'],
            "HealthBehaviours":Zscores['County']['HealthBehaviours'],
            "ClinicalCare" : Zscores['County']['ClinicalCare'], 
            "EconomicFactors" : Zscores['County']['EconomicFactors'],
            "PhysicalEnvironment":Zscores['County']['PhysicalEnvironment']
          }})
    return jsonify(sample_list)            

# Route to display the all the geographical & demographics information about the county in the given state  
@app.route("/countygeodetails/<state>")
def geodemo(state):
    sample_list=[]

    # Get only the state selected by the user
    for item in db.State.find({'StateName': state}):
        State_Counties = item['Counties']
        
        for geodemo in State_Counties:
            sample_list.append({geodemo['County']['CountyName']:{  
            'Latitude' : geodemo['County']['Latitude'],
            'Longitude' : geodemo['County']['Longitude'],
            'TotalArea' : geodemo['County']['TotalArea'],
            'Population' : geodemo['County']['Population'],
            'geodemo.CountyWikiLink' : geodemo['County']['CountyWikiLink']
            }})
    return jsonify(sample_list)            

# Route to display the all the information about the given state    
@app.route("/countyalldetails/<state>")
def details(state):
    sample_list = []
    
    for item in db.State.find({'StateName': state}):
        Statedetaildict = {}
        Statedetaildict['State'] = item['StateName']
        Statedetaildict['Year'] = item['Year']
        Statedetaildict['FIPS'] = item['FIPS']
        Statedetaildict['Counties'] = item['Counties']
        sample_list.append(Statedetaildict)

    return jsonify(sample_list)        

# RM Added route for UC3
def speakUserSelection(state,topCounty):
    pythoncom.CoInitialize()
    # response = "Hello user! "
    response = "Hello user! " + "You selected " + state + ". It's best county, based on your selection is "+ topCounty   
    response += ".  All the best in your search for a good place to live in " + topCounty
    speak = wc.Dispatch("Sapi.SpVoice")
    speak.speak(response)

# User selection is sent
@app.route('/attributeSelection/<userSelection>')
def result(userSelection):
    selection = {}
    
    ## Splitting the user selections with ':' as the delimiter that was constructed in JS
    selections = userSelection.split(':')

    for select in selections:
            ## Splitting the user selections by '_'
            preferences = select.split('_')
            # populate the selection dictionary only if user selection is not empty
            if (preferences[0] not in selection and preferences[1] !='empty'):
                selection[preferences[0]] = preferences[1]

    #   Get the Top 3 counties per user selection
    top3Counties = []
    topCounty = ""
    State = ""
    if(len(selection)>0):
        userPref = CountySelection(selection) 
        userPref = userPref.Selection()
        RecommendedCounty ={}
        
        for  index , row in userPref.iterrows():
            RecommendedCounty =  {'AggregatedValue': row['AggregatedValue'],
            'CountyName':row['CountyName'], 
            'CountyWikiLink': row['CountyWikiLink'], 
            'Latitude' : row['Latitude'],
            'Longitude' : row['Longitude'], 
            'Population': row['Population'], 
            'StateLatitude' : row['StateLatitude'], 
            'StateLongitude' : row['StateLongitude'],
            'StateName' : row['StateName'], 
            'StateShortName': row['StateShortName'], 
            'TotalArea' : row['TotalArea']
            }
            if (State == ''):
                topCounty = row['CountyName']
                State = row['StateName']
            top3Counties.append(RecommendedCounty)
    
    speakUserSelection(State,topCounty)
    #   Send back the html back to user
    return jsonify(top3Counties)
  

#------------------------------------------------------------------------------------#
# Initiate Flask app
#------------------------------------------------------------------------------------#
if __name__=="__main__":
    connect_args={'check_same_thread':False} 
    # InitializeDataBase() 
    app.run(debug=True)
    

