# Message to send the client

Plain English, ready to forward. Background is in
`2026-10-07-google-ads-api-access-application.md`.

---

Hi,

We need one small thing from you so we can finish the audit tool.

**What the problem is**

The API token you gave us is at "Test" level. At that level Google only lets us
read test accounts, not real ones. Only you can raise it, because the token
belongs to your account.

**What to do**

1. Open <https://ads.google.com> and sign in with your **manager account**. This
   is the Google Ads account that manages your other accounts. It is the same
   login you used when you created the API token.
2. At the top right, click the **tools icon** (it looks like a wrench).
3. Click **Setup**, then **API Center**.
4. You will see your token, and next to it a line called **Access level**. It
   will say **Test**, **Basic** or **Standard**.
5. **Send us a screenshot of that page**, or just tell us that one word.

That is all we need to know first. If it already says Basic or Standard, there
is nothing more for you to do.

**If it says Test**

On the same page there is a button to apply for Basic access. Please click it
and fill in the form.

Two details it asks for are ours:

- Google Cloud project ID: `ppcway-509313`
- Google Cloud project number: `734687676224`

Where it asks how you will use the API, please copy and paste this:

> PPCWay is an onboarding and optimisation service for small businesses that
> advertise on Google. A business owner connects their own Google Ads account
> with OAuth, read only, and we produce an audit of it alongside checks of their
> website and Google Business Profile. We read campaign structure, search term
> reports, keyword Quality Score, impression share and ad policy status. Each
> account is read at the owner's request, after they have granted access, and
> nothing is changed without their explicit approval of the specific change.

**If you cannot find API Center**

It only appears on a manager account. If you do not see it, you are signed in to
a normal ads account. Click your picture at the top right, switch to the manager
account, and look again.

**One last thing**

Google will reply by email, usually within a few days. They sometimes ask a
question or two, and they close the application if nobody answers. Please
forward us anything they send on the same day, and we will write the answer for
you.

Thank you.
