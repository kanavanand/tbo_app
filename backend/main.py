import os
import json
from scp.agents import *
from scp.scp import *
import requests
from flask_cors import CORS
from flask import Flask, request ,jsonify

app = Flask(__name__)
CORS(app, resources={r"/city_info": {"origins": "*"}})
CORS(app, resources={r"/package_info": {"origins": "*"}})
CORS(app, resources={r"/flight_info": {"origins": "*"}})
CORS(app, resources={r"/hotel_info": {"origins": "*"}})


# OPEN_API_KEY= "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"
# openai.api_key= OPEN_API_KEY
from openai import OpenAI
client = OpenAI()


@app.route('/health_check', methods=['GET'])
def health_check():
    return {'response':200}

@app.route('/package_info', methods=['GET'])
def ai_city_info():
    package = request.args.get('package')
    response = get_package_info(package)
    return jsonify({'answer': response})

@app.route('/city_info', methods=['GET'])
def package_info():
    city = request.args.get('city')
    special_request = request.args.get('special_request')
    response = give_trip_info(city,special_request)
    city_params = get_city_params(city)
    file_path='response.json'
    with open(file_path, 'w') as json_file:
        json.dump(response, json_file, indent=2)

    return jsonify({'answer': response, "city_params":city_params})


@app.route('/flight_info', methods=['GET'])
def flight_details():
    file_path='response.json'
    package = request.args.get('package')
    
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)

    input_iten = [i for i in data if package == i['package_name']][0]['text']
    # print(input_iten)
    itinerary_json = parse_itinerary(input_iten)
    print(itinerary_json)

    itinerary_json['cleaned_flight'] = clean_flight_response(itinerary_json['flights'])
    flight_response = [search_flight(origin=plan['flight_origin'],destination=plan['flight_dest'],formatted_date=plan['flight_start']) for plan in itinerary_json["cleaned_flight"]]
    flight_response_ = [resp for resp in  flight_response if isinstance(resp , dict)]
    return jsonify({'answer': flight_response_})


@app.route('/hotel_info', methods=['GET'])
def hotel_details():
    file_path='response.json'
    package = request.args.get('place')
    
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)

    input_iten = [i for i in data if package == i['package_name']][0]['text']
    print(input_iten)
    itinerary_json = parse_itinerary(input_iten)
    print(itinerary_json)

    hotels = itinerary_json['hotels'][0]

    place = hotels['location']
    checkin = hotels['checkin']
    checkout = hotels['checkout']
    
    response = agent_workers( f"search hotels with hotel codes in  {place} from {checkin} to {checkout}" )
    print(response)
    try:
        hotel_code = response[0]['HotelCode']
    except:
        hotel_code = '1218141'

    hotel_details = get_hotel_details(hotel_code)
    return jsonify({'answer': hotel_details['HotelDetails']})

if __name__ == '__main__':
    app.run(host='0.0.0.0',
            port=8080,
            debug = True)
