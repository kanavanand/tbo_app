

import llama_index
import nest_asyncio
from agent_pack.step import LLMCompilerAgentWorker
import json
from typing import Sequence, List
from llama_index.llms import OpenAI, ChatMessage
from llama_index.tools import BaseTool, FunctionTool
from llama_index.agent import AgentRunner
import nest_asyncio
import requests
import json

import pandas as pd
from openai import OpenAI
client = OpenAI()
df = pd.read_csv('/Users/kanavanand/Documents/hackathons/voyage/notebook/city_data.csv')
def hotel_search(number_of_adults , CheckIn , CheckOut, CityCode):
    """
    Perform a hotel search using the TBOHolidays Hotel API.

    Parameters:
    - number_of_adults (int): Number of adults for the hotel search.
    - check_in (str): Check-in date in the format 'YYYY-MM-DD'.
    - check_out (str): Check-out date in the format 'YYYY-MM-DD'.
    - CityCode(str): code of destination city we get from get_city_code city function
    Returns:
    - dict: JSON response containing hotel search results.

    Example:
    >>> result = hotel_search(number_of_adults=1, check_in='2024-01-27', check_out='2024-01-28', "126632")
    
    """

    url = "http://api.tbotechnology.in/TBOHolidays_HotelAPI/HotelSearch"

    payload = json.dumps({
      "CheckIn": CheckIn,
      "CheckOut": CheckOut,
      "HotelCodes": "",
      "CityCode": CityCode,
      "GuestNationality": "IN",
      "PreferredCurrencyCode": "INR",
      "PaxRooms": [
        {
          "Adults": number_of_adults,
          "Children": 0,
          "ChildrenAges": []
        }
      ],
      "IsDetailResponse": True,
      "ResponseTime": 23,
      "Filters": {
        "MealType": "All",
        "Refundable": "true",
        "NoOfRooms": 0
      }
    })
    headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Basic aGFja2F0aG9udGVzdDpIYWNANDgyOTg3OTk='
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.json()['HotelSearchResults'][:5]


def get_city_code(city_name, country_name):
    """
    Retrieve the destination code for a given city and country.

    Parameters:
    - city_name (str): Lowercase city name (e.g., 'london').
    - country_name (str): Lowercase country name (e.g., 'united kingdom').

    Returns:
    - int: Destination code for the specified city and country. Returns default code (126632)
           if the city-country combination is not found.

    Example:
    >>> destination_code = get_city_code(city_name='london', country_name='united kingdom')
    >>> print(destination_code)

    """
    
    val = df.loc[(df.CityName == city_name) & (df.CountryName == country_name), 'DestinationId']
    if not val.empty:
        return val.values[0]
    else:
        return 126632

    
    
def get_hotel_details(hotel_code):
    """
    Retrieve details for a specific hotel using the TBOHolidays Hotel API.

    Parameters:
    - hotel_code (str): The unique code identifying the hotel.

    Returns:
    - dict: JSON response containing details about the specified hotel.

    Example:
    >>> hotel_info = get_hotel_details(hotel_code='ABC123')
    >>> print(hotel_info)
    {'hotel_name': 'Example Hotel', 'location': 'City, Country', ...}
    """
    
    url = "http://api.tbotechnology.in/TBOHolidays_HotelAPI/Hoteldetails"

    payload = json.dumps({
      "Hotelcodes": hotel_code,
      "Language": "en"
    })
    headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Basic aGFja2F0aG9udGVzdDpIYWNANDgyOTg3OTk='
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json()




nest_asyncio.apply()

from llama_index.llama_pack import download_llama_pack
download_llama_pack(
    "LLMCompilerAgentPack",
    "./agent_pack",
    skip_load=True,
)

nest_asyncio.apply()

hotel_search_tool = FunctionTool.from_defaults(fn=hotel_search)

city_code_tool = FunctionTool.from_defaults(fn=get_city_code)

get_hotel_tool = FunctionTool.from_defaults(fn= get_hotel_details) 

hotel_tools = [city_code_tool,hotel_search_tool]



from llama_index.llms import OpenAI, ChatMessage
llm = OpenAI(model="gpt-4-1106-preview")


callback_manager = llm.callback_manager

def convert_json(outpur):
    pompt=f"""
   convert below output to proper json.just return json no explanation needed.
   {outpur}

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
    return json.loads(text)



def agent_workers(query = "search hotels with hotel codes in delhi from 3 march,2024 to 7 th march? "):

    agent_worker = LLMCompilerAgentWorker.from_tools(
                    hotel_tools,
                    llm=llm,
                    verbose=True,
                    callback_manager=callback_manager
    )
    agent = AgentRunner(agent_worker, callback_manager=callback_manager)

    response = agent.chat(query )
    tasks = agent.list_tasks()
    task_state = tasks[-1]
    task_state.task.input
    completed_steps = agent.get_completed_steps( task_state.task.task_id )
    input_string = completed_steps[0].output.response
    print(input_string)
    json_data = convert_json(input_string)
    return json_data


