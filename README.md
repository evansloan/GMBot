# GMBot

## Setup

Get a GroupMe Access Token by logging in to [dev.groupme.com](https://dev.groupme.com/), then follow the steps.

1. **Clone the repo**

    ```
    $ git clone https://github.com/evansloan/GMBot.git
    ```


2. **Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli#download-and-install)**

3. **Log into Heroku CLI**

    ```
    $ heroku login
    ```

4. **Create a Heroku app and push code**

    ```
    $ cd GMBot/ && heroku create APP_NAME

    $ heroku git:remote -a APP_NAME

    $ git add . && git commit -m "initial commit"

    $ git push heroku master

    $ heroku ps:scale web=1 worker=1
    ```

5. **Install required Heroku add-ons**

    The Heroku app utilizes the heroku-postgresql add-on for database functionality, and the heroku-redis add-on for handling requests that take longer than 30 seconds to complete.

    ```
    $ heroku addons:create heroku-redis && heroku addons:create heroku-postgresql
    ```

6. **Set required environment variables**

    ```
    $ heroku config:set GROUPME_TOKEN=GROUPME API KEY BASE_URL=https://APP_NAME.herokuapp.com APP_SETTINGS=src.config.ProductionConfig
    ```

7. **Set up the database**

    ```
    $ heroku run:python manage.py create_db
    ```

7. **Create a GroupMe bot**

    Go to the [GroupMe bots](https://dev.groupme.com/bots) page and click the "Create Bot" button.

    Select the group the bot will live in as well as any name/avatar you would like.

    The callback URL should be the URL for the Heroku app set up previously + /callback. Example: `https://APP_NAME.herokuapp.com/callback`

8. **Initialize the bot**

    Within the GroupMe group the bot is located in, send a message containing the command `!initialize`. This creates a database entry for the group as well as all the members in the group.

If all of the above steps are followed correctly, the bot should be fully functional. You can check the bot's status by checking the Heroku app logs.

```
$ heroku logs -t -a APP_NAME
```
