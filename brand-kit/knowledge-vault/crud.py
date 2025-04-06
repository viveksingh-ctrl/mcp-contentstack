import os 
from mcp.server.fastmcp import FastMCP 
import requests 
from dotenv import load_dotenv 


# Load environment variables
load_dotenv()

# API endpoints
url = {
    "brand_kit": 
        {
            "knowledge_vault": "https://ai.contentstack.com/brand-kits/v1/knowledge-vault/"
        }
}

headers = {
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "authtoken": os.environ.get('AUTHTOKEN'),
    "brand_kit_uid": os.environ.get('BRAND_KIT_UID'),
    "content-type": "text/plain;charset=UTF-8",
}

# Create server with random instance number to avoid conflicts
server = FastMCP(
    name="BrandKit",
    instructions='''You are a manager of a Contentstack product called BrandKit. That manages the content that is being published. 
                   ''',
    dependencies=["requests", "python-dotenv"]
)

@server.tool()
def add_knowledge_vault(text: str) -> str:
    payload = {
        "_metadata": {
            "tags": [],
            "title": " ".join(text.split(' ')[:4])
        },
        "content": text
    }

    response = requests.post(url['brand_kit']['knowledge_vault'], headers=headers, json=payload)
    return f"Knowledge Vault Content created with the following details {str(response.json())}"

@server.tool()
def update_knowledge_vault(content_uid: str, text: str, title: str) -> str:
    payload = {}
    if title:
        payload = {
            "_metadata": {
                "tags": [],
                "title": title
            },
        }
    payload['content'] = text
    response = requests.put(url['brand_kit']['knowledge_vault'] + content_uid, headers=headers, json=payload)
    return f"Knowledge Vault Content Updated with the following details {str(response.json())}"

@server.tool()
def delete_knowledge_vault(content_uid: str) -> str:
    response = requests.delete(url['brand_kit']['knowledge_vault'] + content_uid, headers=headers)
    return f"Knowledge Vault Content Deleted with the following details {str(response.json())}"

@server.tool()
def search_knowledge_vault(content: str) -> str:
    payload = {"content": content}
    response = requests.put(url['brand_kit']['knowledge_vault'] + 'search', headers=headers, json=payload)
    return f"Knowledge Vault Content Updated with the following details {str(response.json())}"

if __name__ == "__main__":
    server.run()