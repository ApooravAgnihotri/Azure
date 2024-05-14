from dotenv import dotenv_values 
# specify the name of the .env file name 
env_name = "local.settings.env"
config = dotenv_values(env_name)

print("---- configuration loaded ----")

# Load Azure SQL database connection details
server = config["server"] 
database = config["database"] 
username = config["username"] 
password = config["password"] 
driver = '{ODBC Driver 18 for SQL Server}'

import pyodbc
table_name = "vwEdrLogsDetailByShivi" 
cnxn = pyodbc.connect(f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}')  
cursor = cnxn.cursor()  
print(cursor.execute(f'select * from {table_name};'))
results = cursor.fetchall()

print()
# for row in results:
#     print(row)
print("------------")


from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from langchain_community.utilities.sql_database import SQLDatabase

db_config = {  
    'drivername': 'mssql+pyodbc',  
    'username': username + '@' + server,  
    'password': password,  
    'host': server,  
    'port': 1433,  
    'database': database,  
    'query': {'driver': 'ODBC Driver 18 for SQL Server'}  
}  

db_url = URL.create(**db_config)
db = SQLDatabase.from_uri(db_url)
print(db)
print("------------")



from langchain_openai.chat_models import AzureChatOpenAI

#setting Azure OpenAI env variables

# os.environ["OPENAI_API_TYPE"] = "azure"
# os.environ["OPENAI_API_VERSION"] = "2023-03-15-preview"
# os.environ["OPENAI_API_BASE"] = "xxx"
# os.environ["OPENAI_API_KEY"] = "xxx"

openai_api_type = config["openai_api_type"]
openai_api_key = config['openai_api_key']
openai_api_base = config['openai_api_base']
openai_api_version = config['openai_api_version'] 

llm = AzureChatOpenAI(deployment_name="gpt-35-turbo", temperature=0, max_tokens=4000 , api_version= openai_api_version)

print(llm)
print("------------")


from langchain.agents.agent_toolkits import SQLDatabaseToolkit
#from langchain.sql_database import SQLDatabase
#from langchain_community.agents.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase  # Updated path for SQLDatabase


toolkit = SQLDatabaseToolkit(db=db, llm=llm)
print(toolkit)
print("------------")


from langchain.agents import AgentExecutor , create_sql_agent  
from langchain.agents.agent_types import AgentType

agent_executor = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
)

#agent_executor.run("how many columns are there in the vwEdrLogsDetailByShivi table?")
final_answer = agent_executor.run("give me detail of row where EdrLogId equal to 2595549 ")

if final_answer:
  print(final_answer)
else:
  print("Final Answer not found in the output.")

