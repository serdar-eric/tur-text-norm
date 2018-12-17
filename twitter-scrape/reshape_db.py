import sys
from os import path

# package hack :(
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from utils import connect_database, get_twitter_config


TWITTER_CONFIG_FILE = "./twitter_config.json"

cf = get_twitter_config(TWITTER_CONFIG_FILE)
DATABASE_NAME = cf["database"]["name"]
RAW_COLLECTION = cf["database"]["raw_collection"]
PROCESSED_COLLECTION = cf["database"]["processed_collection"]

db = connect_database(DATABASE_NAME)
tweets = db.tweets

pipeline = [
    {
        "$match": {
            "$or": [
                {"possibly_sensitive": False},
                {"possible_sensitive": {"$exists": False}},
            ]
        }
    },  # eliminates possibly sensitive tweets
    {
        "$project": {
            "timestamp_ms": 1,
            "tweet_id": "$id_str",
            "full_text": {
                "$cond": {
                    "if": {"$eq": ["$truncated", True]},
                    "then": "$extended_tweet.full_text",
                    "else": "$text",
                }
            },
            "user.id": "$user.id_str",
            "user.name": 1,
            "user.screen_name": 1,
            "user.verified": 1,
            "user.followers_count": 1,
            "user.lang": 1,
            "entities": {
                "$cond": {
                    "if": {"$eq": ["$truncated", True]},
                    "then": "$extended_tweet.entities",
                    "else": "$entities",
                }
            },
            "is_extended": "$truncated",
            "is_retweeted": {"$and": ["$retweeted_status", 1]},
            "is_quoted": "$is_quote_status",
            "retweet": {
                "$cond": {
                    "if": {"$and": ["$retweeted_status", 1]},
                    "then": {
                        "timestamp_ms": "$retweeted_status.timestamp_ms",
                        "tweet_id": "$retweeted_status.id_str",
                        "full_text": {
                            "$cond": {
                                "if": {"$eq": ["$retweeted_status.truncated", True]},
                                "then": "$retweeted_status.extended_tweet.full_text",
                                "else": "$retweeted_status.text",
                            }
                        },
                        "is_extended": "$retweeted_status.truncated",
                        "entities": {
                            "$cond": {
                                "if": {"$eq": ["$retweeted_status.truncated", True]},
                                "then": "$retweeted_status.extended_tweet.entities",
                                "else": "$retweeted_status.entities",
                            }
                        },
                        "user": {
                            "id": "$retweeted_status.user.id_str",
                            "screen_name": "$retweeted_status.user.screen_name",
                            "verified": "$retweeted_status.user.verified",
                            "follower_count": "$retweeted_status.user.followers_count",
                            "lang": "$retweeted_status.user.lang",
                        },
                    },
                    "else": "$$REMOVE",
                }
            },
            "quote": {
                "$cond": {
                    "if": {"$and": ["$quoted_status", 1]},
                    "then": {
                        "timestamp_ms": "$quoted_status.created_at",
                        "tweet_id": "$quoted_status.id_str",
                        "full_text": {
                            "$cond": {
                                "if": {"$eq": ["$quoted_status.truncated", True]},
                                "then": "$quoted_status.extended_tweet.full_text",
                                "else": "$quoted_status.text",
                            }
                        },
                        "is_extended": "$quoted_status.truncated",
                        "entities": {
                            "$cond": {
                                "if": {"$eq": ["$quoted_status.truncated", True]},
                                "then": "$quoted_status.extended_tweet.entities",
                                "else": "$quoted_status.entities",
                            }
                        },
                        "user": {
                            "id": "$quoted_status.user.id_str",
                            "screen_name": "$quoted_status.user.screen_name",
                            "verified": "$rquoted_status.user.verified",
                            "follower_count": "$quoted_status.user.followers_count",
                            "lang": "$quoted_status.user.lang",
                        },
                    },
                    "else": "$$REMOVE",
                }
            },
        }
    },
    {"$out": PROCESSED_COLLECTION},
]
if __name__ == "__main__":
    db[RAW_COLLECTION].aggregate(pipeline=pipeline)
