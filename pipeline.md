1. "Research on a full list of major events especially concerts in Macau in 2025 and get me a data table with the even name, host company, the date, and the potential impact to the local travel business in a scaled number from zero up to one." => Grok, ChatGPT, Perplexity, Gemini

2. "here is an excel file containing 4 tabs of Macau 2025 events. Please help me to 2 things: 1. identify items with missing exact date and do research and find and fill in exact dates for them; 2. merge the 4 tabs and create a new tab contain all events from the 4 without duplication. For repeated items, check date and see if aligned, and use average for the impact scores." => Grok

3. "Analyze the impact of each of the events / concerts in Macau on the Chinese audience, focusing on influence of the pop star involved, if any. Limit the analysis to 50 posts or web articles, prioritizing sources from mainland China, Macau, and Hong Kong. Output in JSON with event_name, organizer name, date, impact_score (0-1), and a 50-word reasoning for the impact scoring." => Grok => events.json

4. load_events.py => events_expanded.json

5. load_events_mongo.py => events collection in MongoDB

6. fetch_DSEC.py => DSEC (ggr, hotel occupancy, visitation) collection in MongoDB

7. fetch_YF_FRED.py => YF_FRED (various finance & economic indicator) collection in MongoDB

8. main_fastapi.py => run server

9. visit 127.0.0.1:8000 from browser
