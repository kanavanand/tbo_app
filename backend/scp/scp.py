import pandas as pd
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import openai
import pandas as pd
import re
from faker import Faker
from openai import OpenAI
client = OpenAI()

fake = Faker()

def generate_hotel_data(checkin, location, checkout):
    hotel_name = fake.company()
    image_url = fake.image_url()
    hotel_id = fake.uuid4()

    return {
        "id": hotel_id,
        "checkin": checkin,
        "location": location.capitalize(),
        "checkout": checkout,
        "hotel_name": hotel_name,
        "image_url": image_url,
    }

def generate_hotels_data(hotel_data_list):
    hotels_data = []

    for hotel_data in hotel_data_list:
        hotel = generate_hotel_data(hotel_data["checkin"], hotel_data["location"], hotel_data["checkout"])
        hotels_data.append(hotel)

    return hotels_data


def calculate_total_nights(itinerary):
    try:
        # Split the itinerary into individual destinations
        destinations = itinerary.split(" → ")

        # Initialize a variable to store the total number of nights
        total_nights = 0

        # Iterate through each destination and extract the number of nights
        for destination in destinations:
            # Extract the number of nights using regular expression
            match = re.search(r'(\d+)N', destination)

            # If a match is found, add the number of nights to the total
            if match:
                total_nights += int(match.group(1))

        return total_nights
    except Exception as e:
        print(f"Error: {e}")
        return 0


def score_packages(pkgs,special_request):
    special_req_params={
    "budget_friendly": False,
    "lengthy_trip": False,
    "adventurous": False,
    "cultural": False,
    "family": False,
    "solo_traveler": False,
    "preferred_climate": False,
    "luxury_travel": False,
    "business_trip": False,
    "conver_multiple_places":False
    }   

    pompt=f"""
    based on below request
    "{special_request}"
    modify the special params
    {json.dumps(special_req_params)}
    only change if told to do so, dont assume anything
    make it true/false depending on request and return json only, no explanation required

    """

    messages= [{'role': 'system','content': pompt}]

    response = client.chat.completions.create(
            model='gpt-4',
            messages=messages,
            temperature=0,
            max_tokens=2048,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

    text = response.choices[0].message.content

    special_req_params_gpt = json.loads(text)
    print(special_req_params_gpt)
    special_req_tags={
      "budget_friendly": ["budget", "economical", "affordable", "cost-effective", "inexpensive", "wallet-friendly"],
      "lengthy_trip": ["long-duration", "extended-stay", "prolonged", "extended", "lengthy"],
      "adventurous": ["adventurous", "exciting", "thrilling", "daring", "bold", "intrepid", "desert-safari", "dhow-cruise"],
      "cultural": ["cultural", "heritage", "traditional", "authentic", "ethnic", "folk", "historical"],
      "family": ["family", "inclusive", "kid-friendly", "child-friendly", "family-oriented", "group-friendly"],
      "solo_traveler": ["solo", "single", "individual", "solitary", "alone", "independent"],
      "preferred_climate": ["climate", "weather", "tropical", "temperate", "warm", "sunny", "ideal-weather"],
      "luxury_travel": ["luxurious", "luxury", "premium", "deluxe", "opulent", "lavish", "high-end"],
      "business_trip": ["business", "corporate", "professional", "work-related", "executive", "commercial"],
      "conver_multiple_places":[]
    }
    # print("*"*100)
    search_params=[]
    for i in special_req_params_gpt.keys():
        if special_req_params_gpt[i]:
            search_params+=special_req_tags[i] 
    # print("-"*100)
    pkgs['score'] =pkgs.package_name.apply(lambda x: len([i for i in search_params if i in x]))
    if special_req_params_gpt['conver_multiple_places']:
        pkgs['score']+=pkgs.text.apply(len)

    if special_req_params_gpt['lengthy_trip']:
        pkgs['score']+=pkgs.text.apply(calculate_total_nights)
    pkgs = pkgs.sort_values(by='score',ascending=False)
    # print("pkgs")
    # print(pkgs.head())
    return pkgs

def get_best_time(soup):
    try:
        best_time_tag = [i for i in soup.find(class_='objective-information mb-5 destination-atf negative-margin-mobile').find_all('p') if "Best Time:" in i.text ][0]
        best_time_text = best_time_tag.find('b').next_sibling.strip()
        if best_time_text:
            return best_time_text.split('/')
        else:
            print("Best Time not found in the HTML.")
            return None
    except:
        return None
    
def get_ideal_duration(soup):
    try:
        ideal_duration = [i.text.split(': ')[1] for i in soup.find(class_='objective-information mb-5 destination-atf negative-margin-mobile').find_all('p') if "Ideal duration:" in i.text ][0]
        return ideal_duration
    except:
        return None

def get_city_params(city):
    url = f"https://www.holidify.com/places/{city}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    best_time = get_best_time(soup)
    ideal_duration = get_ideal_duration(soup)
    return {
        "best_time":best_time,
        "ideal_duration":ideal_duration
    }

def get_package_name(url):
    # Parse the URL
    parsed_url = urlparse(url)

    # Get the path from the parsed URL
    path = parsed_url.path

    # Split the path by '/'
    path_segments = path.split('/')

    # Filter out empty segments
    path_segments = [segment for segment in path_segments if segment]

    # The package name might be the last non-empty segment
    if path_segments:
        package_name = path_segments[-1]
        return package_name
    else:
        return None
    

def get_package_info(package):
    url = f"https://www.holidify.com/package/{package}"
    response = requests.get(url)
    soup_ = BeautifulSoup(response.text, 'html.parser')
    packages_sp = soup_.find(class_="row no-gutters mb-50")
    day_iten=[] 
    for i in packages_sp.find_all(class_ = 'day-item-section w-100'):

        obj={}
        obj['title'] = i.find(class_ = 'title').text
        obj['description']=i.find(class_='description').text
        day_iten.append(obj)
    details={}
    details['day_wise_plan'] = day_iten
    title_ = soup_.find(class_='col-12 col-md-7').find('h1').text
    details['title'] = title_
    # try:
    # prompt=f"""
    # In the below JSON, 
    # For each day_wise_plan convert the description into 3 crisp and to the  point bullet points.
    # Return json object only without any explanation
    # {details}
    # """
    # messages= [{'role': 'system','content': prompt}]

    # response = openai.ChatCompletion.create(
    #         model='gpt-4',
    #         messages=messages,
    #         temperature=0,
    #         max_tokens=2048,
    #         top_p=1,
    #         frequency_penalty=0,
    #         presence_penalty=0
    #     )

    # text = response["choices"][0]["message"]["content"]
    # details = json.loads(text)
    return details
    # except:
    #     return details

def give_trip_info(city,special_request,detailed=False):
    # URL to scrape
    try:
        url = f"https://www.holidify.com/web/ajaxWeb/getFilteredPackages.hdfy?packageFilter=%7B%22sortby%22%3A%22priceLowHigh%22%7D&placeCode={city}"

        # Send an HTTP request to the URL
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

        else:
            print(f"Failed to retrieve the page. Status code: {response.status_code}")

        trip_ = []

        for sp in soup.find_all(class_='row no-gutters inventory-card'):
            obj = {}
            obj['text'] = sp.find(class_='places-covered').text
            obj['image_link'] = sp.find('img')['data-original']
            obj['trip_link']=sp.find('a')['href']
            obj['est_cost'] = sp.find(class_='price').text
            try:
                obj['duration'] = sp.find(class_='pretitle').text
            except:
                pass
            obj['package_name'] = get_package_name( obj['trip_link'] )
            if detailed:
                response = requests.get(obj['trip_link'])
                soup_ = BeautifulSoup(response.text, 'html.parser')
                obj['detailed_itinerary'] = soup_.find(class_="row no-gutters mb-50").text
            trip_.append(obj)

        try:
            trip_df = pd.DataFrame(trip_)
            trip_df=  score_packages(trip_df,special_request)
            trip_ = trip_df.to_dict(orient='records')
            return trip_
        except:
            return trip_
    except:
        return []
    


import json

def _gen_token():
    url = "http://api.tektravels.com/SharedServices/SharedData.svc/rest/Authenticate"

    payload = json.dumps({
      "ClientId": "ApiIntegrationNew",
      "UserName": "Hackathon",
      "Password": "Hackathon@1234",
      "EndUserIp": "192.168.11.120"
    })
    headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Basic aGFja2F0aG9udGVzdDpIYWNANDgyOTg3OTk='
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    token_id = response.json()['TokenId']
    
    return token_id


def search_flight(origin,destination,formatted_date):
    token_id = _gen_token()
    url = "http://api.tektravels.com/BookingEngineService_Air/AirService.svc/rest/Search"
    payload = json.dumps({
      "EndUserIp": "192.168.10.10",
      "TokenId": token_id,
      "AdultCount": "1",
      "ChildCount": "0",
      "InfantCount": "0",
      "DirectFlight": "true",
      "OneStopFlight": "false",
      "JourneyType": "1",
      "PreferredAirlines": None,
      "Segments": [
        {
          "Origin": origin,
          "Destination": destination,
          "FlightCabinClass": "1",
          "PreferredDepartureTime": formatted_date,
          "PreferredArrivalTime": formatted_date
        }
      ],
      "Sources": None
    })
    headers = {
      'Content-Type': 'application/json'
    }
    
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        a= response.json()
        obj={}

        obj['airline'] = a['Response']['Results'][0][0]['Segments'][0][0]['Airline']['AirlineName']

        obj['fare']  = a['Response']['Results'][0][0]['Fare']['OfferedFare']

        obj['Origin'] = a['Response']['Results'][0][0]['Segments'][0][0]['Origin']

        obj['Destination'] = a['Response']['Results'][0][0]['Segments'][0][0]['Destination']
        return obj
    except:
        print(response.json())
        return "None"


import json
from datetime import datetime, timedelta

def parse_itinerary(input_string):
    input_string+=" → Delhi(0N)"
    segments = input_string.split(" → ")
    itinerary = {"flights": [], "hotels": []}

    current_date = datetime.strptime("2024-03-01", "%Y-%m-%d")
    current_location = "delhi"

    for segment in segments:
        location, nights_str = segment.split("(")
        nights = int(nights_str[:-1].replace('N',''))
        if location.lower() != current_location.lower():
            # Add flight details
            flight = {
                "flight_start": current_date.strftime("%Y-%m-%d"),
                "flight_origin": current_location.lower(),
                "flight_dest": location.lower()
            }
            itinerary["flights"].append(flight)

        # Add hotel details
        if nights!=0:
            checkin_date = current_date.strftime("%Y-%m-%d")
            checkout_date = (current_date + timedelta(days=nights)).strftime("%Y-%m-%d")
            hotel = {"checkin": checkin_date, "location": location.lower(), "checkout": checkout_date}
            itinerary["hotels"].append(hotel)

        # Update current location and date for the next iteration
        current_location = location
        current_date = current_date + timedelta(days=nights)

    return itinerary

def clean_flight_response(flight_response):
    
    pompt=f"""
    in below response, replace all the origin and destination with IATA codes. 
    only return the response and whererver you dont find code, put "none".
    Please make sure , you are only put code if you are condifdent

    {json.dumps(flight_response)}
    """

    messages= [{'role': 'system','content': pompt}]

    response = client.chat.completions.create(
                model='gpt-4',
                messages=messages,
                temperature=0,
               
            )
    print(response)
    text = response.choices[0].message.content

    return json.loads(text)