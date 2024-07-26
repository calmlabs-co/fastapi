import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackClient:
  def __init__(self, bot_token, user_token):
    self.bot_client = WebClient(token=bot_token)
    self.user_client = WebClient(token=user_token)
    self.my_user_info = self.get_my_user_info()
    self.users = self.fetch_all_users()
    self.user_groups = self.fetch_all_user_groups()
    self.my_user_groups = self.find_user_groups_for_user(self.my_user_info['id'])

  def fetch_all_users(self):
    all_users = []
    cursor = None

    while True:
      try:
        if cursor:
            response = self.user_client.users_list(cursor=cursor)
        else:
            response = self.user_client.users_list()

        all_users.extend(response['members'])

        if response['response_metadata']['next_cursor']:
            cursor = response['response_metadata']['next_cursor']
        else:
            break
      except SlackApiError as e:
        if e.response['error'] == 'ratelimited':
          retry_after = int(e.response.headers['Retry-After'])
          print(f"Rate limited. Retrying after {retry_after} seconds...")
          time.sleep(retry_after)
        else:
          raise e

    return all_users

  def get_my_user_info(self):
    try:
      # Verify authentication and get basic user info
      auth_response = self.user_client.auth_test()
      user_id = auth_response['user_id']

      # Get detailed user information
      user_info_response = self.user_client.users_info(user=user_id)
      user_info = user_info_response['user']

      return user_info
    except SlackApiError as e:
      print(f"Error fetching user information: {e.response['error']}")
      raise(e)

  def get_user(self, user_id):
    for user in self.users:
      if user['id'] == user_id:
        return user
    return None

  def get_user_by_name(self, name):
    for user in self.users:
      if user['name'] == name:
        return user
    return None

  def get_user_id_by_name(self, name: str) -> str:
    for user in self.users:
      if user['profile']['display_name'] == name:
        return user['id']
      if user['name'] == name:
        return user['id']
    return None

  def get_user_name(self, user_id: str) -> str:
    matching_users = [user for user in self.users if user['id'] == user_id]
    return matching_users[0]['profile']['display_name_normalized'] if len(matching_users) > 0 else None

  def fetch_all_user_groups(self):
    all_user_groups = []
    cursor = None

    while True:
      try:
        if cursor:
          response = self.user_client.usergroups_list(cursor=cursor, include_users=True)
        else:
          response = self.user_client.usergroups_list(include_users=True)

        all_user_groups.extend(response['usergroups'])

        if response['response_metadata'] and response['response_metadata']['next_cursor']:
          cursor = response['response_metadata']['next_cursor']
        else:
          break

      except SlackApiError as e:
        if e.response['error'] == 'ratelimited':
          retry_after = int(e.response.headers['Retry-After'])
          print(f"Rate limited. Retrying after {retry_after} seconds...")
          time.sleep(retry_after)
        else:
          print(f"Error fetching user groups: {e.response['error']}")
          break
    return all_user_groups

  # Function to find user groups that a specific user is associated with
  def find_user_groups_for_user(self, user_id):
    user_groups_associated = []
    for group in self.user_groups:
        group_id = group['id']
        users_in_group = group['users']
        if user_id in users_in_group:
            user_groups_associated.append(group)

    return user_groups_associated

  def fetch_conversations(self, types='im,mpim,private_channel,public_channel', limit=1000):
    all_messages = []
    cursor = None
    response = self.user_client.conversations_list(types=types)

    while True:
      if cursor:
        response = self.user_client.conversations_list(types=types, exclude_archived=True, limit=limit, cursor=cursor)
      else:
        response = self.user_client.conversations_list(types=types, exclude_archived=True, limit=limit)

      all_messages.extend(response['channels'])
      if response['response_metadata'] and response['response_metadata']['next_cursor']:
        cursor = response['response_metadata']['next_cursor']
      else:
        break

    return all_messages


  # Function to fetch messages from a conversation from oldest timestamp onwards
  def fetch_recent_messages(self, channel_id, oldest_timestamp):
    all_messages = []
    cursor = None

    while True:
      try:
        if cursor:
            response = self.user_client.conversations_history(channel=channel_id, cursor=cursor, oldest=oldest_timestamp, limit=1000)
        else:
            response = self.user_client.conversations_history(channel=channel_id, oldest=oldest_timestamp, limit=1000)

        all_messages.extend(response['messages'])

        if response['response_metadata'] and response['response_metadata']['next_cursor']:
            cursor = response['response_metadata']['next_cursor']
        else:
            break
      except SlackApiError as e:
        if e.response['error'] == 'ratelimited':
            retry_after = int(e.response.headers['Retry-After'])
            print(f"Rate limited. Retrying after {retry_after} seconds...")
            time.sleep(retry_after)
        else:
            raise e

    return all_messages

  def search_recent_dm_messages(self, start_time, query_limit=100):
    all_messages = []
    cursor = None

    while True:
      try:
        if cursor:
          response = self.user_client.search_messages(query=f'is:dm after:{start_time}', cursor=cursor, sort='timestamp', count=query_limit)
        else:
          response = self.user_client.search_messages(query=f'is:dm after:{start_time}', sort='timestamp', count=query_limit)
        all_messages.extend(response['messages']['matches'])

        if response['messages'].get('paging', {}).get('pages', 1) > response['messages']['paging']['page']:
          cursor = response['messages']['paging']['page'] + 1
        else:
          break

      except SlackApiError as e:
        if e.response['error'] == 'ratelimited':
          retry_after = int(e.response.headers['Retry-After'])
          print(f"Rate limited. Retrying after {retry_after} seconds...")
          time.sleep(retry_after)
        else:
          #print response and params
          print(f"Error fetching messages: {e.response['error']}")
          print(start_time)
          print(response)
          print(cursor)
          # raise e
          break

    return {
        'mentioned_handle': self.my_user_info['id'],
        'messages': all_messages
    }


  def search_messages_for_user(self, user_id, start_time, query_limit=100):
    all_messages = []
    cursor = None

    while True:
      try:
        if cursor:
          response = self.user_client.search_messages(query=f'<@{user_id}> after:{start_time}', cursor=cursor, sort='timestamp', count=query_limit)
        else:
          response = self.user_client.search_messages(query=f'<@{user_id}> after:{start_time}', sort='timestamp', count=query_limit)

        all_messages.extend(response['messages']['matches'])

        if response['messages'].get('paging', {}).get('pages', 1) > response['messages']['paging']['page']:
          cursor = response['messages']['paging']['page'] + 1
        else:
          break

      except SlackApiError as e:
        if e.response['error'] == 'ratelimited':
          retry_after = int(e.response.headers['Retry-After'])
          print(f"Rate limited. Retrying after {retry_after} seconds...")
          time.sleep(retry_after)
        else:
          raise e

    return all_messages

  def search_my_direct_mentions(self, start_time):
    user_id = self.my_user_info['id']
    messages = self.search_messages_for_user(user_id, start_time)
    my_mentions = {
        'mentioned_handle': user_id,
        'messages': messages
    }

    return my_mentions

  def search_my_user_group_mentions(self, start_time):
    my_group_mentions = []
    for user_group in self.my_user_groups:
      try:
          user_group_id = user_group['id']
          messages = self.search_messages_for_user(user_group_id, start_time)
          my_group_mentions.append({ 'mentioned_user_id': user_group_id, 'messages': messages })
      except Exception as e:
        print(f"Error fetching messages from {user_group_id}: {e}")
        continue
    return my_group_mentions


  def get_thread_ts_of_message(self, channel_id, thread_ts):
    try:
      response = self.user_client.conversations_replies(channel=channel_id, ts=thread_ts)
      if len(response['messages']) > 0:
        if 'thread_ts' not in response['messages'][0]:
          return None
        return response['messages'][0]['thread_ts']
      else:
        return None

    except SlackApiError as e:
      if e.response['error'] == 'ratelimited':
          retry_after = int(e.response.headers['Retry-After'])
          print(f"Rate limited. Retrying after {retry_after} seconds...")
          time.sleep(retry_after)
      else:
          print(f"Error fetching thread messages: {e.response['error']}")

    return None


  def fetch_thread_messages(self, channel_id, thread_ts):
    all_messages = []
    cursor = None

    while True:
      try:
        if cursor:
          response = self.user_client.conversations_replies(channel=channel_id, ts=thread_ts, cursor=cursor)
        else:
          response = self.user_client.conversations_replies(channel=channel_id, ts=thread_ts)

        all_messages.extend(response['messages'])

        if 'response_metadata' in response and 'next_cursor' in response['response_metadata']:
          cursor = response['response_metadata']['next_cursor']
        else:
          break

      except SlackApiError as e:
        if e.response['error'] == 'ratelimited':
          retry_after = int(e.response.headers['Retry-After'])
          print(f"Rate limited. Retrying after {retry_after} seconds...")
          time.sleep(retry_after)
        else:
          print(f"Error fetching thread messages: {e.response['error']}")
          break

    return all_messages

  def send_dm(self, user_id: str, title, blocks: list):
    try:
        # Open a DM channel with the user
        response = self.bot_client.conversations_open(users=[user_id])
        channel_id = response['channel']['id']

        today_date = datetime.now().strftime("%Y-%m-%d")

        # Send the message
        self.bot_client.chat_postMessage(
            channel=channel_id,
            text=title,
            blocks=blocks
        )
        print(f"Message sent to user {user_id}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")

# test Slack Client
slack_client = SlackClient()
