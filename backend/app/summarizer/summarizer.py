from http.client import HTTPException
import json
import re
from datetime import datetime, timedelta
from backend.app.oauth.v2.endpoints.callback import get_installation, get_user_by_slack_user_id
from backend.app.summarizer.openai import OpenAIClient
from backend.app.summarizer.slack import SlackClient
from backend.app.dependencies.database import get_sync_db
from sqlmodel import select
from backend.app.models.user import User


def summarize_for_slack_user(team_id: str, user_id: str):
    # get bot_token and user_token from database
    db = get_sync_db()

    installation = get_installation(user_id, team_id)
    user = get_user_by_slack_user_id(user_id, team_id)
    user_settings = user.slack_installation_settings
    
    bot_token = installation.bot_token
    user_token = installation.user_token
    slack_client = SlackClient(bot_token, user_token)
    openai_client = OpenAIClient()
    summarizer = Summarizer(slack_client, openai_client)

    now = datetime.now()
    start_from = now - timedelta(days=1)
    
    if now.weekday() == 0:
      start_from = now - timedelta(days=3)

    summarizer.summarize(start_from, user_settings.followed_channels, user_settings.followed_users)

class Summarizer:
  def __init__(self, slack_client: SlackClient, openai_client: OpenAIClient):
    self.slack_client = slack_client
    self.openai_client = openai_client
  
  def summarize(self, start_time, followed_channels=[], followed_users=[]):
    # format timestamps for different slack client methods
    start_timestamp = start_time.timestamp()
    start_time_date_string = start_time.strftime('%Y-%m-%d')
    my_user_info = self.slack_client.my_user_info

    # setup.
    threads = set()
    channels = set()

    # step 1. get all messages from all my DMs
    all_my_mentioned_messages = []
    recent_dm_messages = self.slack_client.search_recent_dm_messages(start_time_date_string)
    for message in recent_dm_messages['messages']:
      # skip if message is from bot
      user = self.slack_client.get_user(message['user'])
      if not user:
        continue
      if user.get('is_bot', False):
        # print skipped message
        print(f"Skipping message from bot {message['username']}")
        continue

      channel_id = message['channel']['id']
      message_ts = message['ts']
      thread_ts = self.slack_client.get_thread_ts_of_message(channel_id, message_ts)

      is_slack_thread = thread_ts is not None
      if is_slack_thread:
        thread_ts = self.slack_client.get_thread_ts_of_message(channel_id, message_ts)
        if thread_ts in threads:
          continue

        thread_messages = self.slack_client.fetch_thread_messages(channel_id, thread_ts)
        all_my_mentioned_messages.append({
          'type': 'direct_message_thread',
          'channel_id': channel_id,
          'thread_ts': thread_ts,
          'messages': thread_messages,
          'mentioned_user_id': my_user_info['id']
        })
        threads.add(thread_ts)
      else:
        if channel_id in channels:
          continue
        messages = self.slack_client.fetch_recent_messages(channel_id, start_timestamp)
        all_messages_with_thread_messages = []
        for message in messages:
          # if message is a thread, add the thread messages after this message
          all_messages_with_thread_messages.append(message)
          if 'thread_ts' in message:
              thread_messages = self.slack_client.fetch_thread_messages(channel_id, message['thread_ts'])
              all_messages_with_thread_messages.extend(thread_messages)
        all_my_mentioned_messages.append({
          'type': 'direct_message',
          'channel_id': channel_id,
          'messages': all_messages_with_thread_messages,
          'mentioned_user_id': my_user_info['id']
        })
        channels.add(channel_id)

    # step 2. get all messages from all my direct mentions
    my_mentions = self.slack_client.search_my_direct_mentions(start_time_date_string)
    for message in my_mentions['messages']:
      # skip if message is from bot
      user = self.slack_client.get_user(message['user'])
      if not user:
        continue
      if user.get('is_bot', False):
        # print skipped message
        print(f"Skipping message from bot {message['username']}")
        continue

      channel_id = message['channel']['id']
      message_ts = message['ts']
      thread_ts = self.slack_client.get_thread_ts_of_message(channel_id, message_ts)

      is_slack_thread = thread_ts is not None
      if is_slack_thread:
        thread_ts = self.slack_client.get_thread_ts_of_message(channel_id, message_ts)
        if thread_ts in threads:
          continue

        thread_messages = self.slack_client.fetch_thread_messages(channel_id, thread_ts)
        all_my_mentioned_messages.append({
          'type': 'thread',
          'channel_id': channel_id,
          'thread_ts': thread_ts,
          'messages': thread_messages,
          'mentioned_user_id': my_user_info['id']
        })
        threads.add(thread_ts)

      else:
        if channel_id in channels:
          continue
        messages = self.slack_client.fetch_recent_messages(channel_id, start_timestamp)
        all_messages_with_thread_messages = []
        for message in messages:
          # if message is a thread, add the thread messages after this message
          all_messages_with_thread_messages.append(message)
          if 'thread_ts' in message:
            thread_messages = self.slack_client.fetch_thread_messages(channel_id, message['thread_ts'])
            all_messages_with_thread_messages.extend(thread_messages)
        all_my_mentioned_messages.append({
          'type': 'channel',
          'channel_id': channel_id,
          'messages': all_messages_with_thread_messages,
          'mentioned_user_id': my_user_info['id']
        })
        channels.add(channel_id)

    # step 3. get all messages from all my group mentions
    my_group_mentions = self.slack_client.search_my_user_group_mentions(start_time_date_string)
    all_group_mentioned_messages = []
    for mention in my_group_mentions:
      mentioned_user_id = mention['mentioned_user_id']
      messages = mention['messages']

      for message in messages:
        print(message)
        try:
          user = self.slack_client.get_user(message['user'])
          if not user:
            continue
          if user.get('is_bot', False):
            # print skipped message
            print(f"Skipping message from bot {message['username']}")
            continue
        except:
          continue

        channel_id = message['channel']['id']
        message_ts = message['ts']
        thread_ts = self.slack_client.get_thread_ts_of_message(channel_id, message_ts)

        is_slack_thread = thread_ts is not None
        if is_slack_thread:
          thread_ts = self.slack_client.get_thread_ts_of_message(channel_id, message_ts)
          if thread_ts in threads:
            continue

          thread_messages = self.slack_client.fetch_thread_messages(channel_id, thread_ts)
          all_group_mentioned_messages.append({
            'type': 'thread',
            'channel_id': channel_id,
            'thread_ts': thread_ts,
            'messages': thread_messages,
            'mentioned_user_id': mentioned_user_id
          })
          threads.add(thread_ts)
        else:
          if channel_id in channels:
            continue
          messages = self.slack_client.fetch_recent_messages(channel_id, start_timestamp)
          all_messages_with_thread_messages = []
          for message in messages:
            # if message is a thread, add the thread messages after this message
            all_messages_with_thread_messages.append(message)
            if 'thread_ts' in message:
              thread_messages = self.slack_client.fetch_thread_messages(channel_id, message['thread_ts'])
              all_messages_with_thread_messages.extend(thread_messages)
          all_group_mentioned_messages.append({
            'type': 'channel',
            'channel_id': channel_id,
            'messages': all_messages_with_thread_messages,
            'mentioned_user_id': mentioned_user_id
          })
          channels.add(channel_id)

    # step 4 - summarize channels that i am following
    channels_following_messages = []
    for channel_id in followed_channels:
      all_followed_channel_messages = []
      if channel_id in channels:
        continue
      messages = self.slack_client.fetch_recent_messages(channel_id, start_timestamp)
      all_messages_with_thread_messages = []
      # if message is a thread, add the thread messages after this message
      for message in messages:
        all_messages_with_thread_messages.append(message)
        if 'thread_ts' in message:
          thread_messages = self.slack_client.fetch_thread_messages(channel_id, message['thread_ts'])
          all_messages_with_thread_messages.extend(thread_messages)
      channels_following_messages.append({
        'type': 'channel',
        'channel_id': channel_id,
        'messages': all_messages_with_thread_messages,
      })

    # step 5 - summarize content of people that I am following
    all_user_mentioned_messages = []
    for user_id in followed_users:
      user_mentioned_messages = self.slack_client.search_messages_for_user(user_id, start_time_date_string)
      for message in user_mentioned_messages:
        # skip if message is from bot
        user = self.slack_client.get_user(message['user'])
        if not user:
          continue
        if user.get('is_bot', False):
          # print skipped message
          print(f"Skipping message from bot {message['username']}")
          continue

        channel_id = message['channel']['id']
        message_ts = message['ts']
        thread_ts = self.slack_client.get_thread_ts_of_message(channel_id, message_ts)

        is_slack_thread = thread_ts is not None
        if is_slack_thread:
          thread_ts = self.slack_client.get_thread_ts_of_message(channel_id, message_ts)
          if thread_ts in threads:
            continue

          thread_messages = self.slack_client.fetch_thread_messages(channel_id, thread_ts)
          all_user_mentioned_messages.append({
            'type': 'following_user_in_thread',
            'channel_id': channel_id,
            'thread_ts': thread_ts,
            'messages': thread_messages,
            'mentioned_user_id': user_id
          })
          threads.add(thread_ts)
        else:
          if channel_id in channels:
            continue
          messages = self.slack_client.fetch_recent_messages(channel_id, start_timestamp)
          all_messages_with_thread_messages = []
          for message in messages:
            # if message is a thread, add the thread messages after this message
            all_messages_with_thread_messages.append(message)
            if 'thread_ts' in message:
                thread_messages = self.slack_client.fetch_thread_messages(channel_id, message['thread_ts'])
                all_messages_with_thread_messages.extend(thread_messages)
          all_user_mentioned_messages.append({
            'type': 'following_user_in_channel',
            'channel_id': channel_id,
            'messages': all_messages_with_thread_messages,
            'mentioned_user_id': user_id
          })
          channels.add(channel_id)

    all_message_sets = all_my_mentioned_messages + all_group_mentioned_messages + channels_following_messages + all_user_mentioned_messages
    combined_text = self._combine_text_for_parsing(all_message_sets)
    print(combined_text)

    summary = self.openai_client.summarize_all_mentions_text(combined_text)
    json_data = json.loads(summary)
    print(json.dumps(json_data, indent=2))

    title = f":newspaper: Your Daily Ketchup Summary for {datetime.now().strftime('%B %d, %Y')} :newspaper:"
    summary_in_slack_blocks = self._create_slack_blocks(json_data)
    print(json.dumps(summary_in_slack_blocks, indent=2))

    user_id = self.slack_client.my_user_info['id']  # Replace with the actual user ID
    self.slack_client.send_dm(user_id, title, summary_in_slack_blocks)

  def _combine_text_for_parsing(self, message_sets):
    text = ""
    for message_set in message_sets:
        if message_set['type'] == 'following_user_in_thread':
            text += f"# start of a direct message thread_ts: {message_set['thread_ts']}, channel_id: {message_set['channel_id']}. I am following the user '{message_set['mentioned_user_id']}':\n"
            text += "\n".join(self._format_messages(message_set['messages']))
            text += "\n\n"
        elif message_set['type'] == 'following_user_in_channel':
            text += f"# start of a public or public channel channel_id: {message_set['channel_id']}."
            text += f"I am following the user '{message_set['mentioned_user_id']}':\n"
            text += "\n".join(self._format_messages(message_set['messages']))
            text += "\n\n"
        elif message_set['type'] == 'direct_message':
            text += f"# start of a direct message channel_id: {message_set['channel_id']}. I am in this message into this as '{message_set['mentioned_user_id']}':\n"
            text += "\n".join(self._format_messages(message_set['messages']))
            text += "\n\n"
        elif message_set['type'] == 'direct_message_thread':
            text += f"# start of a direct message thread_ts: {message_set['thread_ts']}, channel_id: {message_set['channel_id']}. I am tagged into this as '{message_set['mentioned_user_id']}':\n"
            text += "\n".join(self._format_messages(message_set['messages']))
            text += "\n\n"
        elif message_set['type'] == 'thread':
            text += f"# start of a public or public channel thread thread_ts: {message_set['thread_ts']}, channel_id: {message_set['channel_id']}. I am tagged into this as {message_set['mentioned_user_id']}':\n"
            text += "\n".join(self._format_messages(message_set['messages']))
            text += "\n\n"
        else:
            text += f"# start of a public or public channel channel_id: {message_set['channel_id']}."
            text += f"I am tagged into this as '{message_set['mentioned_user_id']}':\n" if 'mentioned_user_id' in message_set else "\n"
            text += "\n".join(self._format_messages(message_set['messages']))
            text += "\n\n"
    return text


  def _replace_user_id_with_mentions(self, body_text: str) -> str:
    """ Replace user IDs in a chat message text with user names.

    Args:
        body_text (str): The text of a chat message.
        users (list): A list of user information dictionaries.
            Each dictionary must have 'id' and 'name' keys.

    Returns:
        str: The text of the chat message with user IDs replaced with user names.

    Examples:
        >>> users = [{'id': 'U1234', 'name': 'Alice'}, {'id': 'U5678', 'name': 'Bob'}]
        >>> body_text = "Hi <@U1234>, how are you?"
        >>> replace_user_id_with_name(body_text, users)
        "Hi @Alice, how are you?"
    """
    pattern = r"(U[A-Z0-9]+)"
    for match in re.finditer(pattern, body_text):
        user_id = match.group(1)
        body_text = body_text.replace(match.group(0), f"<@{user_id}>")
    return body_text

  def _add_priority_emoji(self, priority_text):
    if priority_text == 'Low':
      return ':large_green_circle: Low'
    elif priority_text == 'Medium':
      return ':large_yellow_circle: Medium'
    elif priority_text == 'High':
      return ':red_circle: High'
    else:
      return ''

  def _format_messages(self, messages):
    """
    Format thread messages to be easily parsed into LLM
    """
    messages_text = []
    for message in messages[::]:
        # Ignore bot messages and empty messages
        if "bot_id" in message or len(message["text"].strip()) == 0:
            continue

        # Get message body from result dict.
        body_text = message["text"].replace("\n", "\\n")

        # messages_text.append(f"{speaker_name}: {body_text}")
        messages_text.append(f"{message['user']}: {body_text}")

    if len(messages_text) == 0:
        return []
    else:
        return messages_text

  def _create_slack_blocks(self, json_data):
    blocks = []

    # Create initial
    blocks.append({
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": ":newspaper:  Your Daily Ketchup Summary :newspaper:"
			}
		})

    blocks.append({
			"type": "context",
			"elements": [
				{
					"text": f"*{datetime.now().strftime('%B %d, %Y')}* | What happened yesterday",
					"type": "mrkdwn"
				}
			]
		})

    blocks.append({"type": "divider"})

    # Add follow-up topics header
    blocks.append({
      "type": "header",
      "text": {
          "type": "plain_text",
          "text": ":dart: Actionables"
      }
    })

    for idx, topic in enumerate(json_data["actionables"]):
      action_items_text = 'None'
      if 'action_items' in topic and len(topic['action_items']) > 0:
          action_items_text = "\n".join([f"• {self._replace_user_id_with_mentions(action_item)}" for action_item in topic['action_items']])

      links_text = f"• <{topic['link_to_slack_message']}|Original message>\n"
      if 'links' in topic and len(topic['links']) > 0:
        links_text += "\n".join([f"• <{link['url']}|{link['link_summary']}>" for link in topic['links']])

      blocks.append(
        {
          "type": "section",
          "text": {
              "type": "mrkdwn",
              "text": f"*{idx+1}. {topic['title']}*",
          },
          "fields": [
            {
              "type": "mrkdwn",
              "text": f"*Priority*\n{self._add_priority_emoji(topic['priority'])}"
            },
            {
              "type": "mrkdwn",
              "text": f"*Current Status*\n{self._replace_user_id_with_mentions(topic['current_status'])}"
            },
            {
              "type": "mrkdwn",
              "text": f"*Summary*\n{self._replace_user_id_with_mentions(topic['summary'])}"
            },
            {
              "type": "mrkdwn",
              "text": f"*Action Items*\n{action_items_text}"
            },
            {
              "type": "mrkdwn",
              "text": f"*Links*\n{links_text}"
            },
            {
              "type": "mrkdwn",
              "text": f"*Source*\n<#{topic['channel_id']}>"
            }
          ],
        }
      )
      blocks.append({"type": "divider"})

    # Add interesting topics header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": ":bee: To catch up on"
        }
    })

    for idx, topic in enumerate(json_data["to_catch_up_on"]):
      action_items_text = 'None'
      if 'action_items' in topic and len(topic['action_items']) > 0:
        action_items_text = "\n".join([f"• {self._replace_user_id_with_mentions(action_item)}" for action_item in topic['action_items']])

      links_text = f"• <{topic['link_to_slack_message']}|Original message>\n"
      if 'links' in topic and len(topic['links']) > 0:
        links_text += "\n".join([f"• <{link['url']}|{link['link_summary']}>" for link in topic['links']])

      blocks.append({
          "type": "section",
          "text": {
              "type": "mrkdwn",
              "text": f"*{idx+1}. {topic['title']}*",
          },
          "fields": [
            {
            "type": "mrkdwn",
            "text": f"*Priority*\n{self._add_priority_emoji(topic['priority'])}"
            },
            {
              "type": "mrkdwn",
              "text": f"*Current Status*\n{self._replace_user_id_with_mentions(topic['current_status'])}"
            },
            {
              "type": "mrkdwn",
              "text": f"*Summary*\n{self._replace_user_id_with_mentions(topic['summary'])}"
            },
            {
              "type": "mrkdwn",
              "text": f"*Action Items*\n{action_items_text}"
            },
            {
              "type": "mrkdwn",
              "text": f"*Links*\n{links_text}"
            },
            {
              "type": "mrkdwn",
              "text": f"*Source*\n<#{topic['channel_id']}>"
            }
          ],
      })
      blocks.append({"type": "divider"})
    print(blocks)

    return blocks