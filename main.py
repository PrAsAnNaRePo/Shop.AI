import json
import os
from fastapi import FastAPI
import google.generativeai as genai
from mangum import Mangum
from pydantic import BaseModel
import requests

genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))

app = FastAPI()
handler = Mangum(app)
model = genai.GenerativeModel('gemini-pro')
serper_endpoint = "https://google.serper.dev/shopping"

################ USEFULL FUNCTIONS ################

def get_super_relevent_product(items, query):
    prompt = """Given a list of products (title, source, prics, delivery) and user description, you gotta tell that which one is more like the user need. Pick the one that best suits.
"""
    for item in items:
        prompt += f"titile: {item['title']}\nsource: {item['source']}\nprice: {item['price']}\ndelivery: {item['delivery']}\n\n"

    prompt += f"User description: {query}.\nReturn the related product in JSON model, for example:\n{{\n  \"title\": \"Nike Air Max 90\",\n  \"source\": \"Amazon\",\n  \"price\": \"$100\",\n  \"delivery\": \"2 days\"\n}}\n"
    print(prompt)
    return model.generate_content(prompt).text

################ API ENDPOINTS ################

@app.get("/")
async def msg():
    return {"message": "Hello, you got this!"}

class QueryInput(BaseModel):
    query: str

@app.post("/search")
async def search(query: QueryInput):
    user_query = query.query
    search_keyword = model.generate_content("""You are a Shopping Agent AI. Given a search query of user, generate some consise and crisp keywords for search tool to search for. Use related keywords.
Use next line character to separate the keywords.
For example, if the user query is "I want some best shoes for running", the output should be:
best running shoes in amazon
best running shoes in nike
best running shoes in adidas
shoes for men
Sports shoes
                                 

NOTE:
- Your response should be neatly formatted like above. Use related but different keywords.
- Do not use the same keyword in the response.
- Do not include more than 3 keywords in the response.
- Do not include any special characters in the response like list bullets, commas, etc.

User query: """ + user_query).text.split("\n")
    payload = []
    for keyword in search_keyword:
        payload.append({"q": keyword, "gl": "in", "page": 2, "num": 10})
    headers = {
    'X-API-KEY': os.environ.get('SERPER_API_KEY'),
    'Content-Type': 'application/json'
    }
    serper_results = requests.request("POST", serper_endpoint, headers=headers, data=json.dumps(payload))
    organic_results = []
    for result in serper_results.json():
        for i in result['shopping']:
            organic_results.append(i)
    print(len(organic_results))

    filterd_results = []
    title_filter = []
    for result in organic_results:
        if result['title'] not in title_filter:
            filterd_results.append(result)
            title_filter.append(result['title'])
    mrp = get_super_relevent_product(filterd_results, user_query)
    mrp = json.loads(mrp)
    print(len(filterd_results))
    filterd_results2 = []
    mrp_list = []
    for i in filterd_results:
        if i['title'] != mrp['title']:
            filterd_results2.append(i)
        else:
            mrp_list.append(i)
    return {"mrp": mrp_list, "other": filterd_results2}
