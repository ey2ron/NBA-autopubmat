# Facebook Page Posting — Super Simple Setup

Note: The current app only generates pubmats. Use this guide only if you
decide to re-enable Facebook posting later.

This file shows how to connect the app to Facebook. Read it slowly. It is OK
to take your time. We will do small steps.

You need three things:

1. A Facebook Page you control
2. The Page ID (a number)
3. A long-lived Page Access Token

---

## Step 1 — Make a Facebook Page

1. Go to https://facebook.com
2. Click **Menu** → **Pages** → **Create New Page**
3. Create a Page and remember the name
4. Make sure you are an **Admin** on the Page

---

## Step 2 — Make a Meta App

1. Go to https://developers.facebook.com/apps
2. Click **Create App**
3. If you are asked for **Use cases**, choose **Other** or **None**, then click **Next**
4. Name the app (for example: `nba-pubmat`) and finish creation
5. If you land on a page titled **Use cases**, click **Facebook Login** or **Customize**
6. Open **Permissions and features** if needed, but do not worry about finding `pages_*` there
7. The `pages_show_list`, `pages_read_engagement`, and `pages_manage_posts` permissions are requested later in the Graph API Explorer

---

## Step 3 — Get a short-lived User Token

1. Open the Graph API Explorer: https://developers.facebook.com/tools/explorer/
2. Top right: pick your app from the **Meta App** dropdown
3. Click **Generate Access Token**
4. In the permission picker, check these:
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`
5. Click **Generate Access Token** again and log in
6. Copy the token (this one only lasts about 1 hour)

If you do not see those permissions at first, keep the same app selected and
look in the Graph API Explorer permission picker, not the app dashboard.

---

## Step 4 — Find your Page ID and Page Token

In the Graph API Explorer, keep the token loaded and do this:

1. Request type: `GET`
2. Endpoint: `me/accounts`
3. Click **Submit**
4. In the response, find your Page. You will see:
   - `id` → this is your Page ID
   - `access_token` → this is your Page Token (short-lived)
5. Copy both values somewhere safe

---

## Step 5 — Make a long-lived token (never expires)

We do two small web requests.

### 5a) Exchange for a long-lived user token

Open this URL in your browser. Replace the parts in <>.

```
https://graph.facebook.com/v19.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id=<YOUR_APP_ID>
  &client_secret=<YOUR_APP_SECRET>
  &fb_exchange_token=<SHORT_LIVED_USER_TOKEN>
```

You can find **App ID** and **App Secret** here:
App Dashboard → **Settings** → **Basic**.

The response has a long-lived user token.

### 5b) Use the long-lived user token to get the long-lived page token

Open this URL in your browser (replace the token):

```
https://graph.facebook.com/v19.0/me/accounts?access_token=<LONG_LIVED_USER_TOKEN>
```

Copy the `access_token` that matches your Page. This is your **long-lived
Page Access Token**.

Optional check (should show `"expires_at": 0`):

```
https://graph.facebook.com/debug_token?input_token=<PAGE_TOKEN>&access_token=<PAGE_TOKEN>
```

---

## Step 6 — Put the secrets into the project

1. In the repo root, copy `.env.example` to `.env`
2. Open `.env` and fill in:

```
FB_PAGE_ID=1234567890
FB_PAGE_ACCESS_TOKEN=EAAxxxxxxx...
```

Do NOT commit `.env`. It is already in `.gitignore`.

---

## Step 7 — (Only if your Page is public)

If your Page is public and has real followers, Facebook may require
**App Review** for `pages_manage_posts`. If so, go to:

App Dashboard → **App Review** → **Permissions and Features**.

If your Page is private or just for testing, you can skip this.

---

## Step 8 — Test it

Dry run (no Facebook call):

```powershell
python -m nba_post.main --fixture tests/fixtures/raptors_bucks_2019_g6.json --dry-run
```

Real post:

```powershell
python -m nba_post.main --fixture tests/fixtures/raptors_bucks_2019_g6.json
```

You should see the post on your Page in a few seconds.

---

## Troubleshooting

| Error | Meaning |
| --- | --- |
| `(#200) The user hasn't authorized the application` | You missed a permission in Step 3. |
| `(#190) Error validating access token: Session has expired` | Your token is old. Do Step 5b again. |
| `(#10) Application does not have permission` | Your Page is public and the app is not approved. See Step 7. |
| `Invalid OAuth access token` | You pasted the wrong token. Redo Step 4. |
