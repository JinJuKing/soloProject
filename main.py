import os
from dotenv import load_dotenv
import pyupbit

load_dotenv()

access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")

upbit = pyupbit.Upbit(access, secret)

balances = upbit.get_balances()
print(balances)