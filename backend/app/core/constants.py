# Bot Token Scopes
# Scopes that act on behalf of the bot.

bot_scopes = [
  "channels:history",      # View messages and other content in public channels that Ketchup has been added to
  "channels:join",         # Join public channels in a workspace
  "channels:read",         # View basic information about public channels in a workspace
  "chat:write",            # Send messages as @Slack API Test
  "chat:write.customize",  # Send messages as @Slack API Test with a customized username and avatar
  "chat:write.public",     # Send messages to channels @Slack API Test isn't a member of
  "commands",              # Add shortcuts and/or slash commands that people can use
  "groups:history",        # View messages and other content in private channels that Ketchup has been added to
  "groups:read",           # View basic information about private channels that Ketchup has been added to
  "users:read",            # View people in a workspace,
  "im:history",            # View messages and other content in direct messages that Ketchup has been added to
  "mpim:history",          # View messages and other content in group direct messages that Ketchup has been added to
]


# User Token Scopes
# Scopes that access user data and act on behalf of users that authorize them.

user_scopes = [
  "channels:history",  # View messages and other content in a user's public channels
  "channels:read",     # View basic information about public channels in a workspace
  "groups:history",    # View messages and other content in a user's private channels
  "groups:read",       # View basic information about a user's private channels
  "im:history",        # View messages and other content in a user's direct messages
  "im:read",           # View basic information about a user's direct messages
  "mpim:history",      # View messages and other content in a user's group direct messages
  "mpim:read",         # View basic information about a user's group direct messages
  "usergroups:read",   # View user groups in a workspace
  "users:read"         # View people in a workspace
]
