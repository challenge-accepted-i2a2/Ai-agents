#!/bin/bash

curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "what are the most present products and their quantities?"}'
