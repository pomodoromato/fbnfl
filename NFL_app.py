import requests
from datetime import date
import pandas as pd
import numpy as np
import json
from dataclasses import dataclass
import asyncio
import aiohttp
import streamlit as st
import re



today = (date.today()).strftime("%Y%m%d")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://google.com"
}


async def fetch_teamstats(
                s,
                id
                ):
    async with s.get(f'https://cdn.espn.com/core/nfl/boxscore?xhr=1&gameId={id}') as r:
        if r.status != 200:
            r.raise_for_status()
        return await r.json()


async def fetch_teamstats_all(
                s,
                id_list
                ):
    tasks = []
    for id in id_list:
        task = asyncio.create_task(fetch_teamstats(s, id))
        tasks.append(task)
    res = await asyncio.gather(*tasks)
    
    return res


def filter_json(json_data, 
                filter_criteria):
    """Filter JSON data based on the given criteria.

    Args:
        json_data (list or dict): JSON data to be filtered.
        filter_criteria (callable): A function that takes an item from the JSON data
            as input and returns True if the item should be included in the filtered
            results, or False otherwise.

    Returns:
        list: Filtered JSON data as a list.
    """
    # Check if the input is a list or a dict
    if isinstance(json_data, 
                  list):
        filtered_data = [item for item in json_data if filter_criteria(item)]
    elif isinstance(json_data, dict):
        filtered_data = {key: value for key, value in json_data.items() if filter_criteria(value)}
    else:
        raise ValueError("Input JSON data must be a list or a dictionary.")

    return filtered_data


async def get_schedule(date=today):
    # Get all events
    url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={date}'
    payload = ''
    response = requests.request(
        "GET", 
        url, 
        data=payload,
        headers=headers
        )
    json_response = response.json()
    json_events = json_response['events']

    # Filter down to live events
    def livegame_filter(event):
        return event['status']['type']['state'] == 'in'
        # return event['status']['type']['state'] == 'post'

    live_games = filter_json(
            json_events, 
            livegame_filter
            )

    id_list = [live_game['id'] for live_game in live_games]

    return id_list


async def store_as_json(
            list,
            file_path: str = None
            ):
        """ Dumps the scraped content into a JSON-file in the same 
        directory. Creates the file and prints a confirmation.
        """
        
        if file_path:
            with open(file_path, 'w') as file:
                json.dump(list, file)
            print(f"Content successfully dumped into '{file_path}'")
        else:
            with open('NHL.json', 'w') as file:
                json.dump(list, file)
            print("Content successfully dumped into 'NHL.json'")



async def clean_data(json):
    # Opening JSON file
    # f = open('C:\\Users\\tnytr\\OneDrive\\Desktop\\\\Sportsref\\NCAAFB live stats\\ncaafb_liveteamstats.json')

    # returns JSON object as
    # a dictionary
    games = json

    data = []
    stats_data = []
    for game in games:
        try:
            away_row = {
                'Match': f"{game['gamepackageJSON']['boxscore']['teams'][0]['team']['displayName']} vs {game['gamepackageJSON']['boxscore']['teams'][1]['team']['displayName']}",
                'Team': game['gamepackageJSON']['boxscore']['teams'][0]['team']['displayName'],
                'Score': float(game['gamepackageJSON']['header']['competitions'][0]['competitors'][1]['score']),
                # 'timeouts_used': game['gamepackageJSON']['header']['competitions'][0]['competitors'][1]['timeoutsUsed']
            }
        except:
            continue
        
        try:
            home_row = {
                'Match': f"{game['gamepackageJSON']['boxscore']['teams'][0]['team']['displayName']} vs {game['gamepackageJSON']['boxscore']['teams'][1]['team']['displayName']}",
                'Team': game['gamepackageJSON']['boxscore']['teams'][1]['team']['displayName'],
                'Score': float(game['gamepackageJSON']['header']['competitions'][0]['competitors'][0]['score']),
                # 'timeouts_used': game['gamepackageJSON']['header']['competitions'][0]['competitors'][0]['timeoutsUsed']
            }
        except:
          continue

        data.append(away_row)
        data.append(home_row)


        away_stats = game['gamepackageJSON']['boxscore']['teams'][0]['statistics']
        away_stat_values = [item['displayValue'] for item in away_stats]
        away_stat_labels = [item['label'] for item in away_stats]
        # away_stat_dict = {key: value for key, value in zip(away_stat_labels, away_stat_values)}
        away_stat_dict = {}
        for key, value in zip(away_stat_labels, away_stat_values):
            if re.match(r'^\d+-\d+$', value):
                away_stat_dict[key] = value  # Keep "x-y" values as text
            else:
                try:
                    away_stat_dict[key] = float(value)  # Try to convert other values to numbers
                except ValueError:
                    away_stat_dict[key] = value


        
        home_stats = game['gamepackageJSON']['boxscore']['teams'][1]['statistics']
        home_stat_values = [item['displayValue'] for item in home_stats]
        home_stat_labels = [item['label'] for item in home_stats]
        # home_stat_dict = {key: value for key, value in zip(home_stat_labels, home_stat_values)}
        home_stat_dict = {}
        for key, value in zip(home_stat_labels, home_stat_values):
            if re.match(r'^\d+-\d+$', value):
                home_stat_dict[key] = value  # Keep "x-y" values as text
            else:
                try:
                    home_stat_dict[key] = float(value)  # Try to convert other values to numbers
                except ValueError:
                    home_stat_dict[key] = value

        stats_data.append(away_stat_dict)
        stats_data.append(home_stat_dict)
    df_data = pd.DataFrame.from_records(data)
    df_stats = pd.DataFrame(stats_data)
    df = pd.concat([df_data, df_stats], axis=1)
    print(df.to_html)


    # Function to calculate the conversion percentage in ratio x-y
    def calculate_conversion_percentage(row):
        success, total = map(int, row.split('-'))
        if total == 0:
            return 0
        return (success / total) * 100

    # Apply the function to create the new column
    
    # df['3rd down %'] = df['3rd down efficiency'].apply(calculate_conversion_percentage)
    # df['4th down %'] = df['4th down efficiency'].apply(calculate_conversion_percentage)
    
    try:
        df['Pass Comp %'] = df['Comp-Att'].apply(calculate_conversion_percentage)
        df['Pass Comp %'] = df['Pass Comp %'].round(0)
    except:
        print('damn')
    # try:
    #     df['3rd down att'] = df['3rd down efficiency'].str.split('-').str[1]
    # except:
    #     print('oopss')
    # try:
    #     df['3rd down att'] = pd.to_numeric(df['3rd down att'], errors='coerce')
    # except:
    #     print('oops')
    # try:
    #     df['4th down att'] = df['4th down efficiency'].str.split('-').str[1]
    # except:
    #     print('oops')
    # try:
    #     df['4th down att'] = pd.to_numeric(df['4th down att'], errors='coerce')
    # except:
    #     print('oops')
    try:
        df['Pass comp'] = df['Comp-Att'].str.split('-').str[0]
    except:
        print('oops')
    try:
        df['Pass comp'] = pd.to_numeric(df['Pass comp'], errors='coerce')
    except:
        print('odsops')
    try:
        df['Pass Attempts'] = df['Comp-Att'].str.split('-').str[1]
    except:
        print('oops')
    try:
        df['Pass Attempts'] = pd.to_numeric(df['Pass Attempts'], errors='coerce')
    except:
        print('oops')


    try:
        df['% Pass Plays'] = df['Pass Attempts']/(df['Rushing Attempts']+df['Pass Attempts'])
    except:
        print('oops')

    try:
        df['% Rush Plays'] = df['Rushing Attempts']/(df['Rushing Attempts']+df['Pass Attempts'])
        df['% Rush Plays'] = df['% Rush Plays'].round(2)*100
    except:
        print('oops')
    try:
        df['% Pass Plays'] = df['% Pass Plays'].round(2)*100
    except:
        print('osops')

    final_df = df[[
            'Match',
            'Team',
            'Score',
            'Pass Attempts',
            'Pass Comp %',
            '% Pass Plays',
            '% Rush Plays',
            'Rushing Attempts',
            'Rushing',
            'Passing',
            'Pass comp',
            'Yards per pass',
            'Yards per rush',
            'Total Yards'
            ]]
    return final_df

async def update(pass_df,
                 rush_df,
                 complete_df):
    st.write("""
    # 🏈 NFL Drivesss

    ## Passss
    """)
    st.write(pass_df)

    st.write("""
    ## Rush:
    """)
    st.write(rush_df)
    st.write("""
    ## Completions
    """)
    st.write(complete_df)


async def main():
    id_list = await get_schedule(date=today)

    async with aiohttp.ClientSession() as session:
        results = await fetch_teamstats_all(session, id_list)
        df = await clean_data(results)
        pass_df = df[[
            'Team',
            'Pass Attempts',
            '% Pass Plays',
            'Pass Comp %',
            'Passing',
            'Pass comp',
            'Yards per pass',
            'Score'
            ]]
        rush_df = df[[
            'Team',
            'Rushing Attempts',
            '% Rush Plays',
            'Yards per rush',
            'Score'
            ]]
        complete_df = df[[
            'Team',
            'Pass Attempts',
            'Pass Comp %',
            'Passing',
            'Yards per pass',
            'Score'
            ]]


        await update(pass_df,
                     rush_df,
                     complete_df)
        

        # await store_as_json(
        #     list=results, 
        #     file_path="C:\\Users\\tnytr\\OneDrive\\Desktop\\\\Sportsref\\NCAAFB live stats\\ncaafb_liveteamstats.json"
        #     )

if __name__ == "__main__":
    asyncio.run(main())