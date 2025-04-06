from mcp.server.fastmcp import FastMCP 

text = '''
Here's how we knew acquiring a real-time CDP was a smart move for our customers. 

Hint: it's not because they said the words (“I need a real-time CDP”). 

Here's what they did say:

❌ PROBLEM WE HEARD: “I don’t have good first party customer data.”

✅ Our CDP can help you start collecting high-quality data today. The sooner you start, the sooner you can turn that data into valuable insights.

❌ PROBLEM WE HEARD: “My data is sitting in some non real-time data warehouse.”

✅ We hear this a lot.. If all your data is sitting in Snowflake (or somewhere else), and you can’t personalize content because of that, we’ve got you covered. We can merge that data with our brand-aware genAI and automation to turn it into meaningful action.

❌ PROBLEM WE HEARD: “My customer data is siloed across a ton of systems.”

✅ This is a common issue with legacy providers. If your data is stuck in separate systems, we can unify it into a single, actionable profile that can be used across different channels in real time.

We hear you. We’re here to help.

Combining content and data is easier than you think with the right partner. Let’s get started.

'''

server = FastMCP(
    name="Automate",
    instructions='''Automate takes care of the automation around Contentstack. The current server is to fetch data from 
                    Linkedin
                   ''',
    dependencies=["requests", "python-dotenv"]
)

@server.tool()
def get_linkedin_data(name: str) -> str:
    return text

