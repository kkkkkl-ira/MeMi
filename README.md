# MeMi

MeMi is a simple Streamlit MVP that turns a pasted or uploaded meeting transcript into cleaned notes. Each user can temporarily provide their own OpenAI API key in the interface. When no key is provided, MeMi uses local mock output.

## Features

- Paste a raw transcript or upload a UTF-8 `.txt` file
- Choose a cleaned Q&A transcript or concise bullet-point summary
- Optionally add the date, interviewer, company, business, and meeting topic
- Review suspicious industry terms with timestamps and suggested corrections
- Copy the generated notes or download them as Markdown
- Let each user bring their own OpenAI API key (BYOK)
- Generate notes with OpenAI or run locally with mock output

## Project structure

```text
.
├── app.py            # Streamlit interface and mock generator
├── prompts.py        # Prompt templates for both output types
├── requirements.txt  # Python dependency list
└── README.md          # Setup and usage instructions
```

## Setup

You need Python 3.10 or newer.

1. Open a terminal in this project folder.
2. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   ```

3. Activate it:

   macOS or Linux:

   ```bash
   source .venv/bin/activate
   ```

   Windows PowerShell:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

4. Install the dependency:

   ```bash
   pip install -r requirements.txt
   ```

## Use your own OpenAI API key

After MeMi starts, open the **使用你自己的 OpenAI API Key** section at the top of the page and paste your own key into the password field.

- The key is masked in the interface.
- It is stored only in that user's Streamlit session memory.
- It is not written to a file or database by MeMi.
- Each user's API usage is charged to their own OpenAI API account.
- The user can click **清除 Key** to remove it from the current session.
- Do not share keys, include them in screenshots, or commit them to Git.

The server necessarily receives the key in memory to make the OpenAI request. Deploy MeMi only over HTTPS and use a trusted hosting provider. Session memory is temporary, but it is not the same as keeping the key entirely inside the browser.

## Run

```bash
streamlit run app.py
```

Streamlit will show a local address, usually `http://localhost:8501`. Open it in a browser if it does not open automatically.

When a key is configured, the transcript is sent to the OpenAI API using the complete prompt from `prompts.py`. API usage may incur charges on your OpenAI API account.

If the model finds a likely mistranscribed industry term, MeMi shows its timestamp, the original term, a short explanation, and up to two possible corrections. After you confirm the correct wording, MeMi updates the notes locally without making another API request. When no likely terminology errors are found, this review step stays hidden.

Every generated note begins with the meeting date, interviewer, and meeting topic. These fields live in an optional collapsed section; missing values are shown as `未提供` instead of being invented by the model.

## Mock mode

If the user does not enter an API key, `generate_mock_notes()` in `app.py` returns a short sample response without sending the transcript to any AI service. This makes it possible to test the interface without an API account.

## Share with friends

For a simple hosted version, push the project to a GitHub repository and deploy `app.py` with Streamlit Community Cloud or another HTTPS-enabled Python host. Do not configure your personal OpenAI key as a server secret when using BYOK mode. Send friends the deployed URL; each person enters their own key in their own session.
