import requests
from bs4 import BeautifulSoup
import json
import os


def extract_image_urls(data):
    image_urls = set()

    for pin in data:
        image_url = pin['images']['474x']['url']
        image_urls.add(image_url)

    return image_urls


def extract_board_id(input_string):
    import re

    match = re.search(r'board_id="(\d+)"', input_string)
    if match:
        return match.group(1)
    else:
        return None


def fetch_from_bookmark(board_url, board_id, bookmark):
    url = 'https://www.pinterest.com/resource/BoardFeedResource/get/?source_url=/' + board_url + \
        '/&data={"options":{"add_vase":true,"board_id":"' + board_id + \
        '","field_set_key":"react_grid_pin","filter_section_pins":false,"is_react":true,"prepend":false,"page_size":15,"bookmarks":["' + bookmark + '"]}}'

    response = requests.get(url)
    response.raise_for_status()

    result = response.json()
    board_feed_data = result['resource_response']['data']
    image_urls = extract_image_urls(board_feed_data)
    next_bookmark = result['resource']['options']['bookmarks'][0]

    return image_urls, next_bookmark


def fetch_pinterest_board_image_urls(board_url):
    all_urls = set()

    # Fetch the Pinterest board page
    response = requests.get(f"https://www.pinterest.com/{board_url}/")
    response.raise_for_status()

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the script tag with id="__PWS_INITIAL_PROPS__"
    script_tag = soup.find(
        'script', id='__PWS_INITIAL_PROPS__', type='application/json')

    if not script_tag:
        raise ValueError(
            "Could not find the JSON script with id='__PWS_INITIAL_PROPS__'")

    # Parse the JSON content from the script tag
    json_content = script_tag.string
    result = json.loads(json_content)

    # Access the BoardFeedResource
    board_feed_resource = result['initialReduxState']['resources']['BoardFeedResource']

    # Extract the board_id
    board_id = extract_board_id(list(board_feed_resource.keys())[
                                0] if board_feed_resource.keys() else "")

    board_feed_data = {}
    next_bookmark = ""

    # Find the nested attribute that contains the 'data' attribute
    for key, value in board_feed_resource.items():
        if 'data' in value:
            board_feed_data = value['data']
            next_bookmark = value['nextBookmark']
            break
    else:
        raise ValueError("'data' attribute not found in BoardFeedResource")

    # Extract image URLs from the board feed data
    image_urls = extract_image_urls(board_feed_data)
    all_urls.update(image_urls)

    print(f"Found {len(image_urls)} image URLs")

    # Fetch more data using the next bookmark
    while next_bookmark.lower() != "-end-":
        try:
            image_urls, next_bookmark = fetch_from_bookmark(
                board_url, board_id, next_bookmark)
            all_urls.update(image_urls)
            print(f"Found {len(image_urls)} image URLs")
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    print(f"Total image URLs found: {len(all_urls)}")

    return all_urls


def download_image(url, folder_path):
    try:
        print('downloading:', url)
        response = requests.get(url)
        if response.status_code == 200:
            file_path = os.path.join(folder_path, url.split('/')[-1])
            with open(file_path, 'wb') as file:
                file.write(response.content)
    except Exception as e:
        print(f"Failed to download {url}: {e}")


def download_images_from_pinterest_board(board_url, folder_path):

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    image_urls = fetch_pinterest_board_image_urls(board_url)

    for image_url in image_urls:
        try:
            download_image(image_url, folder_path)
        except Exception as e:
            print(f"Failed to download image: {e}")


if __name__ == '__main__':
    board_url = 'username/board'  # Example: 'dakotagoldberg/autumn'
    folder_path = 'downloaded_images'
    download_images_from_pinterest_board(board_url, folder_path)
