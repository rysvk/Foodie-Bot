from typing import Any, Dict, List

import ssl
import smtplib
import pandas as pd
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

# Create a creds.py file in the same folder with these variables
# USERNAME = <sender email id>
# PASSWORD = <email password>
from actions.creds import USERNAME, PASSWORD

# Reading zomato data into a dataframe
ZomatoData = pd.read_csv('zomato.csv')
ZomatoData = ZomatoData.drop_duplicates().reset_index(drop=True)

# Cities from the template have some missing values like Nasik
WeOperate = ['New Delhi', 'Gurgaon', 'Noida', 'Faridabad', 'Allahabad', 'Bhubaneshwar', 'Mangalore', 'Mumbai',
             'Ranchi', 'Patna', 'Mysore', 'Aurangabad', 'Amritsar', 'Puducherry', 'Varanasi', 'Nagpur', 'Vadodara',
             'Dehradun', 'Vizag', 'Agra', 'Ludhiana', 'Kanpur', 'Lucknow', 'Surat', 'Kochi', 'Indore', 'Ahmedabad',
             'Coimbatore', 'Chennai', 'Guwahati', 'Jaipur', 'Hyderabad', 'Bangalore', 'Nashik', 'Pune', 'Kolkata',
             'Bhopal', 'Goa', 'Chandigarh', 'Ghaziabad', 'Ooty', 'Gangtok', 'Shimla']

# Getting Valid cities from the data
WeOperate = ZomatoData['City'].str.lower().value_counts().index

# Here is the output of above operation
# ['new delhi', 'gurgaon', 'noida', 'faridabad', 'allahabad', 'mangalore',
# 'mysore', 'bhubaneshwar', 'ranchi', 'patna', 'aurangabad', 'amritsar',
# 'mumbai', 'ludhiana', 'vizag', 'puducherry', 'kanpur', 'agra',
# 'varanasi', 'nagpur', 'dehradun', 'vadodara', 'indore', 'kochi',
# 'lucknow', 'surat', 'guwahati', 'jaipur', 'ahmedabad', 'bangalore',
# 'hyderabad', 'coimbatore', 'chennai', 'kolkata', 'pune', 'nashik',
# 'bhopal', 'goa', 'chandigarh', 'ghaziabad', 'ooty', 'shimla', 'gangtok',
# 'mohali', 'secunderabad', 'nasik', 'panchkula']

PRICE_RANGE_MAP: Dict = {
    'low': range(300),
    'mid': range(300, 701),
    'high': range(701, 10000)  # Max value in data is 8K in data
}

EMAIL_TEMPLATE: str = """\
From: {}
To: {}
Subject: Foodie Bot Restuarant Results

Here, is a list of restaurant you requested
----
{}
----

FOODIE BOT
"""

SMTP_SERVER: str = 'smtp.gmail.com'
PORT: int = 465


def restaurant_search(city: str, cuisine: str, budget: str, limit: int) -> pd.DataFrame:
    """Function to Search the resultants based on the params from bots"""

    return ZomatoData[(ZomatoData['Cuisines'].apply(lambda x: cuisine.lower() in x.lower())) &
                      # Below == is used to avoid cases like Mumbai & Navi Mumbai
                      (ZomatoData['City'].apply(lambda x: city.lower() == x.lower())) &
                      (ZomatoData['Average Cost for two'].apply(lambda x: x in PRICE_RANGE_MAP[budget]))][
                          ['Restaurant Name', 'Address', 'Average Cost for two',
                           'Aggregate rating']].sort_values(by='Aggregate rating', ascending=False)[:limit]


def remove_newline(input: str) -> str:
    """Remove the new lines from data"""
    input.replace('\n', '')
    input.replace('\n\r', '')
    return input


def format_message(input: pd.DataFrame) -> str:
    """Helper function to format the output"""
    return '\n'.join(input.apply(
        lambda x: f"- {x[0]} in {remove_newline(x[1])} has been rated {x[3]}", axis=1).values.tolist())


class ActionSearchRestaurants(Action):
    def name(self) -> str:
        """Defines the action's name. Used in bot domain"""
        return 'action_search_restaurants'

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[str, Any]
            ) -> List[Dict[str, Any]]:
        """Executing the action."""
        city = tracker.get_slot('location')
        if city.lower() not in WeOperate:
            """Utter no service incase of location not identified"""
            dispatcher.utter_message(response="utter_no_service")
            return []
        cuisine = tracker.get_slot('cuisine')
        budget = tracker.get_slot('budget')
        results = restaurant_search(city, cuisine, budget, 5)

        if results.empty:
            """Utter no results if query returns empty"""
            dispatcher.utter_message(response="utter_no_result")
            return []

        dispatcher.utter_message(format_message(results))
        return []


class ActionSendMail(Action):
    def name(self) -> str:
        """Defines the action's name. Used in bot domain"""
        return 'action_send_mail'

    async def run(self,
                  dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[str, Any]
                  ) -> List[Dict[str, Any]]:
        """Executing the action."""
        email = tracker.get_slot('email')
        city = tracker.get_slot('location')
        budget = tracker.get_slot('budget')
        cuisine = tracker.get_slot('cuisine')
        context = ssl.create_default_context()
        result = format_message(restaurant_search(city, cuisine, budget, 10))
        message = EMAIL_TEMPLATE.format(USERNAME, email, result)
        with smtplib.SMTP_SSL(SMTP_SERVER, PORT, context=context) as server:
            server.login(USERNAME, PASSWORD)
            server.sendmail(USERNAME, email, message)
        dispatcher.utter_message(response="utter_confirm_mail")
        return []


if __name__ == "__main__":
    # Testing few cases
    # print(restaurant_search("Nasik", "Chinese", "mid", 5))
    # print(restaurant_search("New Delhi", "Chinese", "high", 5))
    print(restaurant_search("Noida", "chinese", "mid", 5))
    # print(WeOperate)
