import ast
import json
import re
from openai import OpenAI
import streamlit as st
import os
from urllib.parse import urlparse
import shelve
import requests
import random
import streamlit.components.v1 as components
import google.generativeai as genai


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

# Constants
USER_AVATAR = "👤"
BOT_AVATAR = "🤖"

model = genai.GenerativeModel('gemini-pro')


# Initialize OpenAI client
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Set default OpenAI model
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o-mini-2024-07-18"

# GraphQL endpoint
GRAPHQL_URL = "https://www.shyaway.com/graphql"

# Function to fetch product list
def get_product_list(
    url_key, 
    search_query=None, 
    sort_by="position", 
    sort_direction="asc", 
    page=1, 
    limit=4, 
    token=None
):
    """
    Fetch the product list from the GraphQL API.

    Args:
        url_key (str): URL key for filtering products.
        search_query (str, optional): Search term for product filtering.
        sort_by (str): Sorting criteria ("price", "position", "created_at").
        sort_direction (str): Sort direction ("asc" or "desc").
        page (int): Page number for pagination.
        limit (int): Number of items per page.
        token (str, optional): Authorization token for API access.

    Returns:
        dict: Parsed response containing the product list or an error message.
    """
    # Define the GraphQL query
    query = f"""
    {{
      getProductList(
        urlKey: "{url_key}",
        searchQuery: {f'"{search_query}"' if search_query else "null"},
        sortBy: "{sort_by}",
        sortDirection: "{sort_direction}",
        page: {page},
        limit: {limit}
      ) {{
        status
        message
        data {{
          items {{
            product_link
            sku
            image {{
              url
              width
              height
            }}
            offer_data{{
              label
              color
          }}
          }}
        }}
      }}
    }}
    """

    # Prepare headers
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Send the request
    response = requests.post(GRAPHQL_URL, json={"query": query}, headers=headers)

    # Handle the response
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"HTTP {response.status_code}", "details": response.text}

# Function to load chat history from shelve file
def load_chat_history():
    with shelve.open("chat_history") as db:
        return db.get("messages", [])


# Function to save chat history to shelve file
def save_chat_history(messages):
    with shelve.open("chat_history") as db:
        db["messages"] = messages


def extract_all_query_parameters(content):
    url_pattern = r'https?://[^\s]+'
    matches = re.findall(url_pattern, content)
    relative_urls = []
    
    for full_url in matches:
        parsed_url = urlparse(full_url)
        relative_url = f"{parsed_url.path}?{parsed_url.query}" if parsed_url.query else parsed_url.path
        relative_urls.append(relative_url)
    
    return relative_urls

def extract_all_relative_urls(content):
    """
    Extracts all relative URLs from Markdown-style links in the given text content.

    Args:
        content (str): Text content containing URLs.

    Returns:
        list: List of extracted relative URLs.
    """
    url_pattern = r'\[.*?\]\((https?://[^\)]+)\)'
    matches = re.findall(url_pattern, content)
    relative_urls = [re.sub(r'https?://www\.shyaway\.com/', '', url) for url in matches]
    return relative_urls

def card(product_details):
    if product_details is None:
        st.markdown("No releated images found")
    else:
        rows = len(product_details[:4]) // 4 + (len(product_details[:4]) % 4 > 0)  # Calculate the number of rows

        for row in range(rows):
            cols = st.columns(4, gap="medium")  # 4 columns with equal padding
            for idx, col in enumerate(cols):
                product_idx = row * 4 + idx
                if product_idx < len(product_details):
                    product = product_details[product_idx]

                    # Initialize offer details
                    offer_label = ""
                    offer_color = "#FF5733"  # Default color

                     # Initialize offer details
                    offer_label2 = ""
                    offer_color2 = "#FF5733"  # Default color
                    
    
                    # Handle 'offer' if it's a list
                    if isinstance(product.get("offer"), list):
                        for i, offer in enumerate(product["offer"]):
                            if isinstance(offer, dict):
                                if(i ==0):
                                    offer_label = offer.get("label", "")
                                    offer_color = offer.get("color", "#FF5733")
                                else:
                                    offer_label2 = offer.get("label", "")
                                    offer_color2 = offer.get("color", "#FF5733")

                    with col:
                        # Dynamically add the offer tag only if `offer_label` is not empty
                        if offer_label2 != "":
                            offer_tag = f"""
                            <div style="position: absolute; bottom: 10px; right: 0px; 
                                background-color: {offer_color}; color: white; padding: 4px 8px; 
                                border-radius: 4px; font-size: 12px;">
                                {offer_label}
                            </div>
                            <div style="position: absolute; bottom: 40px; right: 0px; 
                                background-color: {offer_color2}; color: white; padding: 4px 8px; 
                                border-radius: 4px; font-size: 12px;">
                                {offer_label2}
                            </div>
                            """
                        elif offer_label:
                            offer_tag = f"""
                            <div style="position: absolute; bottom: 10px; right: 0px; 
                                background-color: {offer_color}; color: white; padding: 4px 8px; 
                                border-radius: 4px; font-size: 12px;">
                                {offer_label}
                            </div>
                            """
                        else:
                            offer_tag= "" 

                        st.markdown(
                            f"""
                            <div style="text-align: center; margin-bottom: 10px; position: relative;">
                                <!-- Product Image -->
                                <img src="{product['image_url']}" 
                                    style="height: 300px; object-fit: cover; border-radius: 8px;" 
                                    alt="Product Image">
                                
                                {offer_tag}
                           
                            </div>
                            <div style="text-align: center;">
                                <!-- Product Link -->
                                <a href="{product['product_link']}" target="_blank" style="
                                    text-decoration: none; 
                                    background-color: #007BFF; 
                                    color: white; 
                                    padding: 8px 12px; 
                                    border-radius: 12px; 
                                    font-size: 14px; 
                                    display: inline-block;">
                                    {product['sku']}
                                </a>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

def findCategoryFromContentByGpt(query):
    last_prompt =[]
    last_prompt.append({"role":"system","content":"""
    i want to know the category from the query 
categories: Bra, panty, lingerie set,s shapewear, sportswear,nightwear, accessories, clothing 
analysis of the query to find the category is analysis atribute is fabric,color return the category type is common

if common
    output:
    category: common
else 
    output:
    category: bra,panty                   
    """
    })

    last_prompt.append({"role":"user","content":query})
    response = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=last_prompt
        )
    value= response.choices[0].message.content
    category = findCategoryFromContent(value)
    return category


def findCategoryFromContent(content):
    # Define a mapping of keywords to categories
    category_mapping = {
        "shape": "shapewear",
        "bra": "Bra",
        "lingerie": "lingerie-set",
        "sports": "sportswear",
        "cloth": "clothing",
        "accesor": "accessories",
        "pant": "Panty",
    }

    # Create a regex pattern to match any of the keywords
    pattern = r"\b(" + "|".join(category_mapping.keys()) + r")\w*\b"

    # Find all matches in the content
    matches = re.findall(pattern, content, re.IGNORECASE)

    # Map matches to their respective categories
    matched_categories = {category_mapping[match.lower()] for match in matches}

    return matched_categories

def count_no_product_messages(messages):
    return sum(1 for message in messages if message.get("product") is None and message.get("role") == "assistant")

def display_chat_messages():
    for i, message in enumerate(st.session_state.messages):
        # Skip the first user message, if necessary
        if i != 0:
            avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
            with st.chat_message(message["role"], avatar=avatar):
                # Display text content if it exists
                if "content" in message and message["content"]:
                    if "Qno" in message and message["Qno"]:
                         st.markdown(f"**Qno {message['Qno']}:** {message['content']}")
                    else:
                        st.markdown(message["content"])
                        if "product" in message and message["product"] is None:
                             st.image(image="https://www.shyaway.com/media/wysiwyg/Sorry-no-results-found-350-x-350.jpg",width=360)
                             st.markdown("No image found")

                if "usage" in message and message["usage"]:
                    usage = message["usage"]
                    product_count = 0
                    if "product" in message and message["product"] is None:
                        product_count = 0
                    else:
                        product_count = len(message['product'])
                
                    st.markdown(f"*Img Count**:&nbsp;&nbsp;{product_count}")
                # Display the image if image_url exists
                if "product" in message and message["product"]:
                    product_details = message["product"]
                    
                    if isinstance(product_details, list):                        
                        # Check if it's a nested array
                        if all(isinstance(item, list) for item in product_details):
                            for sublist in product_details:
                                # Ensure sublist is not empty and contains valid dictionaries
                                if sublist and isinstance(sublist[0], dict):
                                    url_category = sublist[0].get('url_category', 'No URL Provided')  # Safely get the URL
                                    st.markdown(url_category)
                                    card(sublist)  # Process the sublist
                                else:
                                    st.warning("Invalid sublist structure or empty sublist.")
                        else:
                            # Process if it's not a nested list
                            if all(isinstance(item, dict) for item in product_details):
                                card(product_details=product_details)
                            else:
                                st.warning("Product details are not structured as a list of dictionaries.")
                    else:
                        print("product_details is not an array.")
                else:
                    if(message['role']!="user"):
                        st.warning("No 'product' key in the message or it's empty.")
                        # card(product_details)




# Function to handle chat interaction
def handle_chat_interaction(prompt):
    user_messages = [msg for msg in st.session_state.messages if msg.get("role") == "user"]
    user_messages_count = len(user_messages)

    if(st.session_state.selected_tab !="All"):
        category = st.session_state.selected_tab
    else:
        category = findCategoryFromContent(prompt)
        if category:
            category = list(category)[0]
        else:
            category = findCategoryFromContentByGpt(prompt)
            if category:
                category = list(category)[0]
            else:
                category = "Bra"
    
    st.session_state.messages.append({"role": "user","Qno":user_messages_count, "content": prompt,"category":category})
    
    print(category)
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(f"**Qno {user_messages_count+1}:** {prompt}")

    category_prompts = {
    "Bra": """
   i want answers related to shyaway.com alone
   category : Bra
   offers=buy-3-for-1199,buy-2-for-1299,flat-20%-off,buy-3-for-899,flat-50%-off,flat-40%-off,new-arrival
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints
   fabric=Nylon,Viscose-Spandex,Nylon-Polyester-Spandex,Cotton,Cotton-Spandex,Lace,Mesh,Modal,Polyester-Spandex,Polycotton-Spandex,Satin
   bra-type=Beginners,Bralette,Cami,Everyday,Fashion-Fancy,Minimiser,Push-Up,T-Shirt,Nursing
   bra-feature=backless,bridal,casual,designer,fancy-back,front-open,hi-support,lacework,longline,moulded,no-sag,plus-size,printed,sexy,sleep,transparent  
   bra-coverage=full-coverage,3-4-th-Coverage,Demi-Coverage
   bra-padding=Non-Padded,Padded,Removable-Padding,Lightly-Padded
   bra-wiring=wired,wirefree
   bra-cup-shape=Balconette,Balcony,Full-Cup,Plunge,T-Shirt-Cup
   bra-push-up-level=level-1,level-2,level-3
   bra-closure=back-closure,front-closure,slip-on
   brand=susie,taabu,shyle,shyaway
   size=28(D,DD,E),30(A,B,C,D,DD,E),32(A,B,C,D,DD,E,F,G,H,I,J),34(A,B,C,D,DD,E,F,G,H,I,J),36(A,B,C,D,DD,E,F,G,H,I,J),38(A,B,C,D,DD,E,F,G,H,I),40(B,C,D,DD,E,F,G,H,I,J),42(B,C,D,E,F,G),44(B,C,D,E,F,G),46(B,C,D),48(B,C,D),50(B,C,D),52(B,C,D)
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
   Convert the query into attributes for the Bra category. Match synonyms or contextual words with the listed bra attributes and provide the result in the following format:
   category: bra, url: https://www.shyaway.com/bra-online/?{attribute=value}
   Example : category: bra, url: https://www.shyaway.com/bra-online/?color-family=red,green&size=32B
    """,
    "Panty": """
   category : Panty
   offers=buy-3-for-499,buy-3-for-599,flat-20%-off,flat-30,new-arrival
   brand=susie,taabu,shyle,shyaway
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   size=2xl,2xl-3xl,3xl,4xl,5xl,l,l-xl,m,s,s-m,xl,xs,xxl
   fabric=cotton-spandex,disposable,lace,mesh,modal,nylon,nylon-spandex,polycotton-spandex,polyester-spandex,viscose-spandex
   panty-type=bikini,boy-shorts,cycling-shorts,hipster,period-panty,thong,tummy-tucker
   panty-feature=bridal,casual,lacework,maternity,no-vpl,plus-size,printed,seamless,sexy,transparent
   panty-coverage=full-coverage,low-coverage,medium-coverage,no-coverage
   panty-waist-level=high-waist,low-waist,medium-waist
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
   Convert the query into attributes for the Panty category. Match synonyms or contextual words with the listed panty attributes and provide the result in the following format:
   category: panty, url: https://www.shyaway.com/panty-online/?{attribute=value}
   Example : category: panty, url: https://www.shyaway.com/panty-online/?fabric=cotton&size=XL  
    """,
    "lingerie-set":"""
    i want  answers related to shyaway.com alone
    category : lingerie-set
   offers=buy-3-for-499,buy-3-for-599,flat-20%-off,flat-30,new-arrival
   size=38D/XL,40B/XXL,40C/XXL,40D/XXL,32D/S,32 D/DD,34 D/DD,36 D/DD,38 D/DD'40 D/DD,42 D/DD,44 D/DD,46 D/DD,48 D/DD,50 D/DD,52 D/DD,54 D/DD,56 D/DD,58 D/DD,2XL/3XL,4XL/5XL
   brand=susie,taabu,shyle
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   fabric=cotton-spandex,lace,mesh,nylon-spandex
   lingerieset-type=everyday,fashion-fancy-bra,push-up,t-shirt
   lingerieset-panty-type=bikini,hipster,thong
   lingerieset-feature=bridal,casual,hi-support,lacework,moulded,no-sag,printed,sexy,Transparent
   lingerieset-panty-feature=bridal,transparent,lacework,,casual,sexy,printed
   lingerieset-bra-closure=back-closure,front-closure,side-closure,slip-on
   lingerieset-bra-coverage=demi-coverage,full-coverage,3/4th-coverage
   lingerieset-panty-coverage=full-coverage,medium-coverage,no-coverage,low-coverage
   lingerieset-bra-padding=padded,non-padded
   lingerieset-bra-wiring=wired,wirefree
   lingerieset-panty-waist-level=hi-impact,low-waist,medium-waist
   lingerieset-bra-seam=seamless,seamed,darted
   lingerieset-bra-cup-shape=balconette,balcony,full-cup,plunge,t-shirt-cup
   lingerieset-push-up-level=level-2,level-3
   lingerieset-bra-straps=back-adjustable,detachable,front-adjustable,fully-adjustable,multiway,non-detachable
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
   Convert the query into attributes for the Lingerie Set category. Match synonyms or contextual words with the listed lingerie set attributes and provide the result in the following format:
   category: lingerie-set, url: https://www.shyaway.com/lingerie-set-online/?{attribute=value}
   Example: category: lingerie-set, url: https://www.shyaway.com/lingerie-set-online/?lingerieset-bra-seam=seamless&color-family=skin&size=m  
    """,
    "sportswear": """
    category : sportswear
   offers=flat-20%-off
   size=xs,s,m,l,xl,2xl,3xl,XXL,XXXL
   brand=shyaway,shyle,united-classic,van-heusen
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   sportswear-type=bra,bottoms,tops
   sportswear-feature=racerback,cross-back,leggings,hoodies,seamless,classic-back,crop-top,jackets,shorts,t-back,t-shirt,joggers,skorts,tank
   sportswear-bra-coverage=high-coverage,medium-coverage,low-coverage
   sportswear-bra-impact-level=low-impact,medium-impact,hi-impact
   sportswear-bra-padding=padded,removable-padding
   sportswear-bra-wiring=wirefree
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
   Convert the query into attributes for the Sportswear category. Match synonyms or contextual words with the listed sportswear attributes and provide the result in the following format:
   category: sportswear, url: https://www.shyaway.com/sportswear-online/?{attribute=value}
   Example : category: sportswear, url: https://www.shyaway.com/sportswear-online/?sportswear-bra-impact-level=hi-impact&color-family=blue&size=L&sportswear-type=bra
    """,  
    "sleepwear": """
    category : sleepwear
   fabric=bamboo,cotton,cotton-spandex,lace,mesh,modal,nylon-spandex,polyester-spandex,satin,viscose
   nightwear-feature=intimate,loungewear,maternity,winter-sleepwear
   nightwear-type=babydoll-and-chemise,camisole-and-slip,tops,nightwear-sets,sleep-tee,sleepwear-bottoms,nightgowns,tops
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   size=xs,s,m,l,xl,2xl,3xl,4xl,5xl
   offers=buy-2-for-599,flat-20%-off
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
   Convert the query into attributes for the Sleepwear category. Match synonyms or contextual words with the listed sleepwear attributes and provide the result in the following format:
   category: sleepwear, url: https://www.shyaway.com/sleepwear-online/?{attribute=value}
   example:category: sleepwear, url: https://www.shyaway.com/sleepwear-online/?color-family=pink&size=XL  
    """,
    "shapewear": """
    category : shapewear
   shapewear-type=Saree,Butt Shaper,Tummy Tucker,Body Shaper,Thigh Shaper,Torso Slimmer,Shaping Panty,Mid-Thigh Shaper,Compression Tights
   size=xs,s,m,l,xl,2xl,3xl,4xl,5xl
   brand=mybra,shyle,united-classic
   color-family=grey,black,white,skin,brown,yellow,orange,pink,red,green,blue,purple,prints,multicolor,jacquard
   fabric=nylon-spandex,polycotton-spandex,polyester-spandex,viscose
   offers=flat-20%-off
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
   Convert the query into attributes for the Shapewear category. Match synonyms or contextual words with the listed shapewear attributes and provide the result in the following format:
   category: shapewear, url: https://www.shyaway.com/shapewear-online/?{attribute=value}
   Examples :category: shapewear, url: https://www.shyaway.com/shapewear-online/?shapewear-feature=tummy-tucker&color-family=black  
    """,
    "accessories":"""
    category : accessories
   accessories-type=bra-bag,bra-essentials,hosiery,masks,socks,boob-tape,adhesive-stick-on,silicone-nipple-pad,bra-extender
   brand=shyle
   color-family=grey,black,white,skin,brown,yellow,orange,pink,red,green,blue,purple,prints,multicolor,jacquard
   fabric=cotton-spandex,elastic,eva,lace,mesh,nylon-spandex,polycotton-spandex,polyester-spandex,silicone
   offers=flat-20%-off
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
   Convert the query into attributes for the Accessories category. Match synonyms or contextual words with the listed accessories attributes and provide the result in the following format:
   category: accessories, url: https://www.shyaway.com/accessories-online/?{attribute=value}
   example: category: accessories, url: https://www.shyaway.com/accessories-online/?color-family=skin 
    """,
    "clothing":"""
    category : clothing
   clothing-type=Legwear,Scarves,Shrugs & Jackets,Tops
   size=FZ
   brand=shyle
   fabric=cotton-spandex,disposable,elastic,eva,lace,mesh,nylon-spandex,polycotton-spandex,polyester-spandex,silicone
   color-family=black,blue,brown,green,multicolor,orange,pink,prints,red,skin,white,yellow
   offers=flat-10
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
   Convert the query into attributes for the Accessories category. Match synonyms or contextual words with the listed clothing attributes and provide the result in the following format:
   category: clothing, url: https://www.shyaway.com/clothing-online/?{attribute=value}
   example: category: accessories, url: https://www.shyaway.com/clothing-online/?size=FZ 
    """,
    "All":"""
        I want answers related to **shyaway.com** alone.
category : Bra
   offers=buy-3-for-1199,buy-2-for-1299,flat-20%-off,buy-3-for-899,flat-50%-off,flat-40%-off,new-arrival
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints
   fabric=Nylon,Viscose-Spandex,Nylon-Polyester-Spandex,Cotton,Cotton-Spandex,Lace,Mesh,Modal,Polyester-Spandex,Polycotton-Spandex,Satin
   bra-type=Beginners,Bralette,Cami,Everyday,Fashion-Fancy,Minimiser,Push-Up,T-Shirt,Nursing
   bra-feature=backless,bridal,casual,designer,fancy-back,front-open,hi-support,lacework,longline,moulded,no-sag,plus-size,printed,sexy,sleep,transparent
   bra-coverage=full-coverage,3-4-th-Coverage,Demi-Coverage
   bra-padding=Non-Padded,Padded,Removable-Padding,Lightly-Padded
   bra-wiring=wired,wirefree
   bra-cup-shape=Balconette,Balcony,Full-Cup,Plunge,T-Shirt-Cup
   bra-push-up-level=level-1,level-2,level-3
   bra-closure=back-closure,front-closure,slip-on
   brand=susie,taabu,shyle,shyaway
   size=28(D,DD,E),30(A,B,C,D,DD,E),32(A,B,C,D,DD,E,F,G,H,I,J),34(A,B,C,D,DD,E,F,G,H,I,J),36(A,B,C,D,DD,E,F,G,H,I,J),38(A,B,C,D,DD,E,F,G,H,I),40(B,C,D,DD,E,F,G,H,I,J),42(B,C,D,E,F,G),44(B,C,D,E,F,G),46(B,C,D),48(B,C,D),50(B,C,D),52(B,C,D)
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
category : Panty
   offers=buy-3-for-499,buy-3-for-599,flat-20%-off,flat-30,new-arrival
   brand=susie,taabu,shyle,shyaway
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   size=2xl,2xl-3xl,3xl,4xl,5xl,l,l-xl,m,s,s-m,xl,xs,xxl
   fabric=cotton-spandex,disposable,lace,mesh,modal,nylon,nylon-spandex,polycotton-spandex,polyester-spandex,viscose-spandex
   panty-type=bikini,boy-shorts,cycling-shorts,hipster,period-panty,thong,tummy-tucker
   panty-feature=bridal,casual,lacework,maternity,no-vpl,plus-size,printed,seamless,sexy,transparent
   panty-coverage=full-coverage,low-coverage,medium-coverage,no-coverage
   panty-waist-level=high-waist,low-waist,medium-waist
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200

category : lingerie-set
   offers=buy-3-for-499,buy-3-for-599,flat-20%-off,flat-30,new-arrival
   size=38D/XL,40B/XXL,40C/XXL,40D/XXL,32D/S,32 D/DD,34 D/DD,36 D/DD,38 D/DD'40 D/DD,42 D/DD,44 D/DD,46 D/DD,48 D/DD,50 D/DD,52 D/DD,54 D/DD,56 D/DD,58 D/DD,2XL/3XL,4XL/5XL
   brand=susie,taabu,shyle
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   fabric=cotton-spandex,lace,mesh,nylon-spandex
   lingerieset-type=everyday,fashion-fancy-bra,push-up,t-shirt
   lingerieset-panty-type=bikini,hipster,thong
   lingerieset-feature=bridal,casual,hi-support,lacework,moulded,no-sag,printed,sexy,Transparent
   lingerieset-panty-feature=bridal,transparent,lacework,,casual,sexy,printed
   lingerieset-bra-closure=back-closure,front-closure,side-closure,slip-on
   lingerieset-bra-coverage=demi-coverage,full-coverage,3/4th-coverage
   lingerieset-panty-coverage=full-coverage,medium-coverage,no-coverage,low-coverage
   lingerieset-bra-padding=padded,non-padded
   lingerieset-bra-wiring=wired,wirefree
   lingerieset-panty-waist-level=hi-impact,low-waist,medium-waist
   lingerieset-bra-seam=seamless,seamed,darted
   lingerieset-bra-cup-shape=balconette,balcony,full-cup,plunge,t-shirt-cup
   lingerieset-push-up-level=level-2,level-3
   lingerieset-bra-straps=back-adjustable,detachable,front-adjustable,fully-adjustable,multiway,non-detachable
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
category : sportswear
   offers=flat-20%-off
   size=xs,s,m,l,xl,2xl,3xl,XXL,XXXL
   brand=shyaway,shyle,united-classic,van-heusen
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   sportswear-type=bra,bottoms,tops
   sportswear-feature=racerback,cross-back,leggings,hoodies,seamless,classic-back,crop-top,jackets,shorts,t-back,t-shirt,joggers,skorts,tank
   sportswear-bra-coverage=high-coverage,medium-coverage,low-coverage
   sportswear-bra-impact-level=low-impact,medium-impact,hi-impact
   sportswear-bra-padding=padded,removable-padding
   sportswear-bra-wiring=wirefree
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
category : sleepwear
   fabric=bamboo,cotton,cotton-spandex,lace,mesh,modal,nylon-spandex,polyester-spandex,satin,viscose
   nightwear-feature=intimate,loungewear,maternity,winter-sleepwear
   nightwear-type=babydoll-and-chemise,camisole-and-slip,tops,nightwear-sets,sleep-tee,sleepwear-bottoms,nightgowns,tops
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   size=xs,s,m,l,xl,2xl,3xl,4xl,5xl
   offers=buy-2-for-599,flat-20%-off
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
category : shapewear
   shapewear-type=Saree,Butt Shaper,Tummy Tucker,Body Shaper,Thigh Shaper,Torso Slimmer,Shaping Panty,Mid-Thigh Shaper,Compression Tights
   size=xs,s,m,l,xl,2xl,3xl,4xl,5xl
   brand=mybra,shyle,united-classic
   color-family=grey,black,white,skin,brown,yellow,orange,pink,red,green,blue,purple,prints,multicolor,jacquard
   fabric=nylon-spandex,polycotton-spandex,polyester-spandex,viscose
   offers=flat-20%-off
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200

 category : accessories
   accessories-type=bra-bag,bra-essentials,hosiery,masks,socks,boob-tape,adhesive-stick-on,silicone-nipple-pad,bra-extender
   brand=shyle
   color-family=grey,black,white,skin,brown,yellow,orange,pink,red,green,blue,purple,prints,multicolor,jacquard
   fabric=cotton-spandex,elastic,eva,lace,mesh,nylon-spandex,polycotton-spandex,polyester-spandex,silicone
   offers=flat-20%-off
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200

category : clothing
   clothing-type=Legwear,Scarves,Shrugs & Jackets,Tops
   size=FZ
   brand=shyle
   fabric=cotton-spandex,disposable,elastic,eva,lace,mesh,nylon-spandex,polycotton-spandex,polyester-spandex,silicone
   color-family=black,blue,brown,green,multicolor,orange,pink,prints,red,skin,white,yellow
   offers=flat-10
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200 

    I have listed the categories, types, and other attributes, and if a question is raised, I need to convert it into attributes and return the result. Find synonyms and understand the word’s context to match it with the closest attribute or category values I provided. The result must strictly match the defined attributes or categories, ensuring it is relevant to the context of the query.
	•	Output Format:
If a query is raised, the result should include the category, matched attribute values, and the corresponding URL, structured as follows:
category: {category.lower()}, url: https://www.shyaway.com/{category.lower()}-online/?{attribute=value}
	•	Justification:
Provide justification for your suggestion in the second line. Explain why the matched attribute or value is suitable by considering the type of support, context, or synonym matching, and ensure the selected values suit the question correctly.
	•	Multiple Values:
If there is more than one matching attribute value, mention them as comma-separated values in the output.
Example : category: bra, url: https://www.shyaway.com/bra-online/?color-family=red,green&size=32B  
"""

}
    common = """
    If no direct match is found, infer the closest matching attribute based on context.
    List multiple matching attribute values as comma-separated.dont divaite from i gave the prompt should provide requested attribute and value if the user ask size you should provide. 
    should provide justify your suggestion
    """
    # Get the specific hello_prompt based on the selected_tab
    hello_prompt = f"{category_prompts.get(category, "")}{common}"

    chat = model.start_chat(history=[])
    chat = model.start_chat(
        history=[
            {"role": "user", "parts": "You are a Shyaway product suggestion assistant. Please ensure that you answer only questions related to Shyaway. If users ask about other brands or companies, respond with: “I’m a Shyaway assistant, and I only provide assistance with Shyaway-related queries."},
            {"role": "user", "parts": f"{hello_prompt}"},
            {"role": "model", "parts": "Sure i will Generate product link from shyaway with justification bassed on the question"},
        ]
    )

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        message_placeholder = st.empty()
        
        response = chat.send_message(prompt)        
        message_placeholder.markdown(response.text)
        # Process the URL key
        url_key = extract_all_relative_urls(response.text)
        if url_key ==[]:
            url_key = extract_all_query_parameters(response.text)
	    
        print(url_key)
        product_details = []  # Default value
        if url_key is not None:
            for url in url_key:
                result = get_product_list(url, page=1, limit=20)
                data = result
                
                if "data" in data and "getProductList" in data["data"]:
                    items = data["data"]["getProductList"]["data"]["items"]
                    random_items = random.sample(items, min(len(items), 20))  # Randomly select up to 4 items
                    url_category = findCategoryFromContent(url)
                    url_category= list(url_category)[0].upper()
                    product_detail = [
                        {
                            'product_link': item['product_link'],
                            'sku': item['sku'],
                            'image_url': item['image']['url'],
                            'offer': item.get('offer_data', {}),
                            'url_category' : url_category
                        }
                        for item in random_items
                    ]
                    product_details.append(product_detail)
    
                    if product_detail:
                        st.markdown(url_category)
                        card(product_detail)
                    else:
                        st.image(image="https://www.shyaway.com/media/wysiwyg/Sorry-no-results-found-350-x-350.jpg",width=360)
                        st.markdown("No image found")
                else:
                    print("Unexpected response:", data)
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": response.text,
            "product": product_details,
            "usage":None,
            "category":st.session_state.selected_tab
        })

    save_chat_history(st.session_state.messages)


def display_total_question_count(placeholder):
    user_messages = [msg for msg in st.session_state.messages if msg.get("role") == "user"]
    total_questions = len(user_messages)+1
    
    no_product_count = count_no_product_messages(st.session_state.messages)
    placeholder.markdown(f"""
    **Total Questions Asked**: {total_questions} 
    **Total No Record Count**: {no_product_count}

    """)



def getBulkQuestion(content):
    questions = []
    current_question = ""
    for line in content.splitlines():
        if line.strip():  # Skip empty lines
            current_question += line.strip() + " "
            if current_question.strip().endswith('?'):
                questions.append(current_question.strip())
                current_question = ""
    return questions


import streamlit as st



def main():
    # Create placeholders for the title and question count
    title_placeholder = st.empty()
    title_placeholder.title("Shyley")

    # Load chat history
    data = load_chat_history()
    if "messages" not in st.session_state:
        st.session_state.messages = data

    # Sidebar with options
    with st.sidebar:
        # Add a unique key to the button
        if st.button("Delete Chat History", key="delete_chat_history_button"):
            st.session_state.messages = []
            save_chat_history([])

        # Placeholder for question count
        question_count_placeholder = st.empty()
        display_total_question_count(question_count_placeholder)

        st.divider()

        # Initialize selected tab in session state
        if "selected_tab" not in st.session_state:
            st.session_state.selected_tab = "All"

        # Use radio buttons to select a tab inside the sidebar
        selected_tab = st.radio(
            "Choose a Category:",
            options=["Bra", "Panty", "lingerie-set","shapewear","clothing","accessories","sportswear","sleepwear","All"],
            index=["Bra", "Panty", "lingerie-set","shapewear","clothing","accessories","sportswear","sleepwear","All"].index(st.session_state.selected_tab),
            horizontal=True,  # Set to False to align vertically in the sidebar
            key="sidebar_radio"  # Unique key for sidebar radio
        )

        st.divider()

        if "qa_state" not in st.session_state:
            st.session_state.qa_state = "bulk"

        qa_state = st.radio(
            "Choose a QA Type:",
            options=["single","bulk"],
            index=["single","bulk"].index(st.session_state.qa_state),
            horizontal= True,
            key="sidebar_radio_qa"
        )

        st.divider()




        # Update session state only if the selected tab changes
        if qa_state != st.session_state.qa_state:
            st.session_state.qa_state = qa_state

        if selected_tab != st.session_state.selected_tab:
            st.session_state.selected_tab = selected_tab

        # Display content based on the selected tab
        if st.session_state.selected_tab == "Bra":
            st.subheader("Bra Section")
            st.write("Explore the latest in bras here!")
        elif st.session_state.selected_tab == "Panty":
            st.subheader("Panty Section")
            st.write("Explore the latest in panties here!")
        elif st.session_state.selected_tab == "Lingerie Set":
            st.subheader("Lingerie Set Section")
            st.write("Explore the latest in lingerie sets here!")
        elif st.session_state.selected_tab == "shapewear":
            st.subheader("Shapewear Section")
            st.write("Explore the latest in Shapewear here!")
        elif st.session_state.selected_tab == "clothing":
            st.subheader("Clothing Section")
            st.write("Explore the latest in Clothing here!")
        elif st.session_state.selected_tab == "accessories":
            st.subheader("Accessories Section")
            st.write("Explore the latest in Accessories  here!")
        elif st.session_state.selected_tab == "sportswear":
            st.subheader("Sportswear Section")
            st.write("Explore the latest in Sportswear  here!")
        elif st.session_state.selected_tab == "sleepwear":
            st.subheader("Nightwear Section")
            st.write("Explore the latest in Nightwear here!")
        else:
            st.subheader("Explore ALl Section")
            st.write("Explore the latest in All lingeries here!")

    # Display all chat messages
    display_chat_messages()

    # Main chat input
    if prompt := st.chat_input("How can I help?"):
        if st.session_state.qa_state == "single":
            handle_chat_interaction(prompt)
        else:
            questions=getBulkQuestion(prompt)
            for q in questions:
                handle_chat_interaction(q)

    components.html("""
        <link rel="stylesheet" href="https://www.gstatic.com/dialogflow-console/fast/df-messenger/prod/v1/themes/df-messenger-default.css">
        <script src="https://www.gstatic.com/dialogflow-console/fast/df-messenger/prod/v1/df-messenger.js"></script>
        <df-messenger
            project-id="circletosearch"
            agent-id="5861dbf5-33bb-4169-a7d9-e5c0059144f2"
            language-code="en"
            max-query-length="-1">
          <df-messenger-chat-bubble
           chat-title="shyley">
          </df-messenger-chat-bubble>
        </df-messenger>
        <style>
          df-messenger {
            z-index: 999;
            position: fixed;
            --df-messenger-font-color: #000;
            --df-messenger-font-family: Google Sans;
            --df-messenger-chat-background: #f3f6fc;
            --df-messenger-message-user-background: #d3e3fd;
            --df-messenger-message-bot-background: #fff;
            bottom: 16px;
            right: 16px;
          }
        </style>
    """, height=800)

if __name__ == "__main__":
    main()
