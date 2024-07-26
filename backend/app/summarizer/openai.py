from openai import OpenAI
import re

TEMPERATURE = 0.3
CHAT_MODEL = "gpt-4o-mini"
DEBUG = True
MAX_BODY_TOKENS = 3000

class OpenAIClient:
  def __init__(self, openai_key, chat_model=CHAT_MODEL, max_body_tokens=MAX_BODY_TOKENS, temperature=TEMPERATURE):
    # self.openai_api_key = os.getenv('OPENAI_API_KEY')
    self.openai = OpenAI(api_key=openai_key)

  def estimate_openai_chat_token_count(self, text: str) -> int:
    """
    Estimate the number of OpenAI API tokens that would be consumed by sending the given text to the chat API.

    Args:
        text (str): The text to be sent to the OpenAI chat API.

    Returns:
        int: The estimated number of tokens that would be consumed by sending the given text to the OpenAI chat API.

    Examples:
        >>> estimate_openai_chat_token_count("Hello, how are you?")
        7
    """
    # Split the text into words and count the number of characters of each type
    pattern = re.compile(
      r"""(
          \d+       | # digits
          [a-z]+    | # alphabets
          \s+       | # whitespace
          .           # other characters
          )""", re.VERBOSE | re.IGNORECASE)
    matches = re.findall(pattern, text)

    # based on https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them
    def counter(tok):
      if tok == ' ' or tok == '\n':
        return 0
      elif tok.isdigit() or tok.isalpha():
        return (len(tok) + 3) // 4
      else:
        return 1

    return sum(map(counter, matches))


  def split_messages_by_token_count(self, messages: list[str]) -> list[list[str]]:
    """
    Split a list of strings into sublists with a maximum token count.

    Args:
        messages (list[str]): A list of strings to be split.

    Returns:
        list[list[str]]: A list of sublists, where each sublist has a token count less than or equal to max_body_tokens.
    """
    body_token_counts = [
      self.estimate_openai_chat_token_count(message) for message in messages
    ]
    result = []
    current_sublist = []
    current_count = 0

    for message, count in zip(messages, body_token_counts):
      if current_count + count <= MAX_BODY_TOKENS:
        current_sublist.append(message)
        current_count += count
      else:
        result.append(current_sublist)
        current_sublist = [message]
        current_count = count

    result.append(current_sublist)
    return result

  def summarize_thread_text(self, text: str, user_id):
    """
    Summarize a chat log in bullet points, in the specified language.

    Args:
        text (str): The chat log to summarize, in the format "Speaker: Message" separated by line breaks.
        language (str, optional): The language to use for the summary. Defaults to "English".

    Returns:
        str: The summarized chat log in bullet point format.

    Examples:
        >>> summarize("Alice: Hi\nBob: Hello\nAlice: How are you?\nBob: I'm doing well, thanks.")
        '- Alice greeted Bob.\n- Bob responded with a greeting.\n- Alice asked how Bob was doing.\n- Bob replied that he was doing well.'
    """


    print(f"Estimated number of tokens: {self.estimate_openai_chat_token_count(text)}")

    response = self.openai.chat.completions.create(
        model=CHAT_MODEL,
        temperature=TEMPERATURE,
        messages=[{
            "role":
            "system",
            "content":
            "\n".join([
                'The chat log format consists of firstly a h1 header that represents the start of a Slack DM, Slack DM thread, Slack thread or a Slack channel followed by the chat log which consists of one line per message in the format "Speaker: Message".',
                "The h1 header also consists of important metadata information that is to be used."
                'Users are represented by IDs that start with U followed by alphanumeric characters. An example is "U01L15W16EP".'
                'Subteams are represented by IDs that start with S followed by alphanumeric characters. An example is "S03FGDTNAAV".'
                "The `\\n` within the message represents a line break."
            ])
        }, {
            "role":
            "user",
            "content":
            "\n".join([
                "I want to understand the summaries of these messages quickly so that I can understand if I need to do anything about it.",
                "Summarize the following chat log into context, situation and then whether it was resolved, followed by anything that I need to follow up on",
                "If there are links to a document that I need to follow up on, please also add the link in markdown format.",
                "If a task is already done and resolved, do not show it.",
                "Indicate who is already assigned to the task.",
                "Indicate if I need to work on it",
                "Include a link to the thread so that I can follow up on it later.",


                f"The chat log is as follows:",
                "",
                text
            ])
        }])

    return response.choices[0].message.content

  def summarize_channel_text(self, text, user_id):
    """
    Summarize a chat log in bullet points, in the specified language.

    Args:
        text (str): The chat log to summarize, in the format "Speaker: Message" separated by line breaks.
        language (str, optional): The language to use for the summary. Defaults to "English".

    Returns:
        str: The summarized chat log in bullet point format.

    Examples:
        >>> summarize("Alice: Hi\nBob: Hello\nAlice: How are you?\nBob: I'm doing well, thanks.")
        '- Alice greeted Bob.\n- Bob responded with a greeting.\n- Alice asked how Bob was doing.\n- Bob replied that he was doing well.'
    """

    print(f"Estimated number of tokens: {self.estimate_openai_chat_token_count(text)}")

    response = self.openai.chat.completions.create(
        model=CHAT_MODEL,
        temperature=TEMPERATURE,
        messages=[{
            "role":
            "system",
            "content":
            "\n".join([
                'The chat log format consists of one line per message in the format "Speaker: Message" within a Slack channel.',
                "The `\\n` within the message represents a line break.",
            ])
        }, {
            "role":
            "user",
            "content":
            "\n".join([
                f"My user_id is {user_id} in the following chat logs.",
                "I want to understand the summaries of these messages quickly so that I can understand if I need to do anything about it.",
                "There might be multiple topics that are discused in the channel.",
                "For each topic, summarize the following chat log into context, situation and then whether it was resolved, followed by anything that I need to follow up on.",
                "If there is a link to a document or meeting invite that I need to follow up on, please also add the link in markdown format."
                "If a task is already done and resolved, do not show it.",
                "Indicate who is already assigned to the task.",
                "Indicate if I need to work on it",
                # "Only show TODOs that have no one assigned, and if I am needed to work on it."


                f"The chat log is as follows:",
                "",
                text
            ])
        }])

    return response.choices[0].message.content

  def summarize_all_mentions_text(self, text: str):
    """
    Summarize a chat log in bullet points.

    Args:
        text (str): The chat log to summarize, in the format "Speaker: Message" separated by line breaks.
        language (str, optional): The language to use for the summary. Defaults to "English".

    Returns:
        str: The summarized chat log in bullet point format.

    Examples:
        >>> summarize("Alice: Hi\nBob: Hello\nAlice: How are you?\nBob: I'm doing well, thanks.")
        '- Alice greeted Bob.\n- Bob responded with a greeting.\n- Alice asked how Bob was doing.\n- Bob replied that he was doing well.'
    """

    print(f"Estimated number of tokens: {self.estimate_openai_chat_token_count(text)}")

    response = self.openai.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.3,
        messages=[{
          "role": "system",
          "content": "\n".join([
              'The chat log format consists of firstly a h1 header that represents the start of a Slack DM, Slack DM thread, Slack thread or a Slack channel followed by the chat log which consists of one line per message in the format "Speaker: Message".',
              "The h1 header also consists of important metadata information that is to be used."
              'Users are represented by IDs that start with U followed by alphanumeric characters. An example is "U01L15W16EP".'
              'Subteams are represented by IDs that start with S followed by alphanumeric characters. An example is "S03FGDTNAAV".'
              "The `\\n` within the message represents a line break."
          ])
        }, {
          "role": "user",
          "content": "\n".join([
            "I want to generate a summary of these messages into topics so that ",
            "I can understand and catch up about work, especially ",
            "if I am required to follow up on them like questions I have not answered, ",
            "or someone is still waiting for me to get back to them.",
            "There might be multiple topics that are discussed in the direct messages, threads or channels.",
            "I might also be wanting to follow people that I have indicated to follow."

            # "I am a Software Engineer. This is a non-exhaustive list of what I am interested in:\n",
            # "- Project Updates: Quick access to recent developments and changes in projects.\n",
            # "- Code Reviews: Notifications of pending code reviews and pull requests.\n",
            # "- Bug Reports: Updates on any new or unresolved bugs assigned to them.\n",
            # "- New Features: Alerts on new tasks or feature implementations.\n",
            # "- Team Collaboration: Insights on team discussions relevant to their work.\n",
            # "- Meeting Summaries: Recaps of meetings they may have missed.\n",
            # "- Deadline Reminders: Reminders of approaching deadlines and milestones.\n",
            # "- Documentation Updates: Notices on updates or changes to project documentation.\n",

            "Overall, please format the topics such that I have: \n",
            "- (1) actionables - Maximum of 8 topics that I need to follow up on. \n",
            "- (2) to_catch_up_on - Maximum of 15 interesting topic to take note of.\n",
            "\n",

            "For each topic in (1) and (2), summarize the following chat log into\n"
            "  - `title`: title\n",
            "  - `channel_id`: the id of the slack channel that this message is in.\n"
            "  - `summary`: describes the background context and a summary of what was discussed, who made those points and the potential impact of what is discussed. \n",
            "  - `current_status`: the current status of the discussion\n",
            "  - `action_items`: a list of strings that represent action items that are planned and have been discussed and assigned to a specific user to work on. Each should describe who will do what.\n",
            "  - `priority`: the priority and urgency of the discussion taking the values 'Low', 'Medium' or 'High'.\n",
            "  - `links`: a list of links to documents or meetings that I need to follow up on. Each link has the keys 'link_summary' and 'url'.\n",
            "  - `link_to_slack_message`: the link to the slack thread or message such as 'https://xendit.slack.com/archives/C06L0DLT48Z/p1721106882.879439'.\n",
            # "  - `participants`: a list of user_ids that are very active in the discussion.\n"

            "Ensure that there are no duplicates across topics in (1) and (2).\n",
            "Finally, return the text in JSON without backticks."

            f"The chat log is as follows:",
            "",
            text
          ])
        }])

    return response.choices[0].message.content

