# TGM AppHub — Setup Instructions

## Step 1 — Open Anaconda Prompt
Search for "Anaconda Prompt" on your computer and open it.

## Step 2 — Go to the AppHub folder
```
cd C:\Users\TGM Education Abuja1\Downloads\apphub
```
(Change the path to wherever you saved the apphub folder)

## Step 3 — Install requirements
```
pip install -r requirements.txt
```

## Step 4 — Run the app
```
streamlit run app.py
```

## Step 5 — Open in browser
Your browser will open automatically at:
```
http://localhost:8501
```

## How to use
- Select **Counsellor** to submit applications and upload documents
- Select **Application Officer** to manage, update and run reports
- Data is saved automatically in the `data/` folder
- Uploaded documents are saved in the `uploads/` folder

## Officer Names
The 10 default officers are: Officer 1 through Officer 10.
To change their names, open `data_manager.py` and edit the `OFFICERS` list.
