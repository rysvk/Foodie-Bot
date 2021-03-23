from typing import Any, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import pandas as pd
import json

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
WeOperate = ZomatoData['City'].value_counts().index

# Here is the output of above operation
#   ['New Delhi', 'Gurgaon', 'Noida', 'Faridabad', 'Ranchi', 'Mangalore',
#    'Aurangabad', 'Bhubaneshwar', 'Mumbai', 'Mysore', 'Amritsar',
#    'Allahabad', 'Patna', 'Dehradun', 'Varanasi', 'Kanpur', 'Vizag',
#    'Vadodara', 'Nagpur', 'Ludhiana', 'Puducherry', 'Agra', 'Kochi',
#    'Lucknow', 'Indore', 'Surat', 'Coimbatore', 'Chennai', 'Bangalore',
#    'Ahmedabad', 'Hyderabad', 'Jaipur', 'Guwahati', 'Pune', 'Kolkata',
#    'Nashik', 'Bhopal', 'Goa', 'Chandigarh', 'Ghaziabad', 'Gangtok', 'Ooty',
#    'Shimla', 'Mohali', 'Secunderabad', 'Nasik', 'Panchkula']

PRICE_RANGE_MAP = {
    'low': range(300),
    'mid': range(300, 701),
    'high': range(701, 10000)  # Max value in data is 8K in data
}


def restaurant_search(city: str, cuisine: str, budget: str, limit: int) -> pd.DataFrame:
    """Function to Search the resultants based on the params from bots"""

    return ZomatoData[(ZomatoData['Cuisines'].apply(lambda x: cuisine.lower() in x.lower())) &
                      # Below == is used to avoid cases like Mumbai & Navi Mumbai
                      (ZomatoData['City'].apply(lambda x: city.lower() == x.lower())) &
                      (ZomatoData['Average Cost for two'].apply(lambda x: x in PRICE_RANGE_MAP[budget]))][
                          ['Restaurant Name', 'Address', 'Average Cost for two',
                           'Aggregate rating']].sort_values(by='Aggregate rating', ascending=False)[:limit]


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

        dispatcher.utter_message('\n'.join(results.apply(
            lambda x: f"{x[0]} in {x[1]} has been rated {x[3]}", axis=1).values.tolist()))
        return []


class ActionSendMail(Action):
    def name(self):
        return 'action_send_mail'

    def run(self, dispatcher, tracker, domain):
        MailID = tracker.get_slot('mail_id')
        sendmail(MailID, response)
        return [SlotSet('mail_id', MailID)]


if __name__ == "__main__":
    # Testing few cases
    print(restaurant_search("Nasik", "Chinese", "mid", 5))
    print(restaurant_search("New Delhi", "Chinese", "high", 5))
