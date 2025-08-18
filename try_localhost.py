#!C:\Program Files\Python27amd64\python.exe
# -*- coding: utf-8 -*-
"""
Author: Sam KARLI
E-mail: karliterv@gmail.com
Date: 
Description:
THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT ANY WARRANTIES OF ANY KIND.
"""
import requests

response = requests.post('http://127.0.0.1:11434/api/generate',
    json={
        'model': 'llama2',
        'prompt': 'Hello, how are you?'
    }
)
print(response.json())

if __name__ == "__main__":
  ""
    pass