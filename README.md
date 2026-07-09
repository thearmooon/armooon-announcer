# armooon cloud announcer

Announces new YouTube uploads in **#youtube** and Twitch going live in **#livestreams**, 24/7 from GitHub's servers — your computer can be off.

## Setup (~5 minutes, all in your browser)

1. **Make two Discord webhooks** (this is the only Discord part):
   - Discord → your server → **Server Settings → Integrations → Webhooks → New Webhook**
   - Webhook 1: name it whatever, channel = **#youtube**, Copy Webhook URL
   - Webhook 2: channel = **#livestreams**, Copy Webhook URL
   - Treat these URLs like passwords — anyone who has one can post in that channel.

2. **Create the GitHub repo**: github.com → New repository → name it `armooon-announcer` → **Public** (public repos get unlimited free Actions minutes; there are no secrets in the code). If you'd rather go Private, edit the cron in the workflow to `*/15 * * * *` to stay inside the free 2,000 min/month.

3. **Upload these files** keeping the folder structure:
   - `announcer.py`
   - `state.json`
   - `.github/workflows/announcer.yml` (easiest: Add file → Create new file → type the full path `.github/workflows/announcer.yml` and paste the contents)

4. **Add the two secrets**: repo → Settings → Secrets and variables → Actions → New repository secret:
   - `DISCORD_YOUTUBE_WEBHOOK` = webhook 1 URL
   - `DISCORD_LIVESTREAMS_WEBHOOK` = webhook 2 URL

5. **Test it**: Actions tab → Announcer → Run workflow (leave "Dry run" checked). Open the run log — you should see something like `seeded state with <videoId>, no announcement; not live`. That means it's working. Future runs happen automatically every ~5 minutes.

## How it avoids double-posting

`state.json` remembers the last announced video ID and whether you were already live; the workflow commits it back after each run. The very first run just records your latest video silently, so nothing old gets re-announced.

## Notes

- GitHub pauses scheduled workflows if a repo has no activity for 60 days — the state commits usually keep it alive, but if you ever notice it stopped, the Actions tab will have an "Enable" button.
- Live alerts detect the stream via your public Twitch page. If Twitch ever changes their page internals, the workflow log will show it and we can patch.
- To change the messages, edit the two `post_webhook(...)` texts in `announcer.py`.
