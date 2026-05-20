# demo-ai-observability

Welcome to this *self-guided* demo repository for AI Observability. During some small exercies you will learn how to quickly setup a AI Observability Lab environment.

This Lab environment exists of:

- Local LLM setup using Ollama and Open WebUI.
- Our preffered model is `gpt-oss:latest`, but you can always pick your own.
- Small AI Agent examples to give a try.





# Setup environment

Ensure you have initialized your local `.env` file. Below a snippet from [example .env](.env-example).

Create your *personal* local *.env* configuration. Take care since this file contains sensitive information.

```
cp .env-example .env
```

```
# Compose settings
COMPOSE_PROJECT_NAME=demo-ai-observability

# Ollama settings
OLLAMA_MODELS=gpt-oss:latest # llama3:latest
OLLAMA_MODEL_DEFAULT=gpt-oss:latest
OPENAI_API_KEY=blaat            # Just a dummy value
```

Now you can spin up your local LLM Setup using Docker Compose (see [compose.yaml](./compose.yaml)). It could take some minutes to initially download the `gpt-oss:latest` or other selected model(s).

```
docker compose up -d
```

Now have a look with `docker ps` or `docker compose status`. Validate if both `ollama` and `open-webui` containers are successfully started and made available through localhost.

If everything is oke, you can do the initial browser login into `Open WebUI` at `http://127.0.0.1:3000`.

![Browser login page](images/openwebui.png)

Now explore the interface and give the *Chat window* a try.

# Buzzword Bingo exercise

This first exercise you will work with both the `agent` and `interactive` version of Buzzword Bingo. Here you will get some idea how *LangChain*, *LangGraph* and *LangFuse* work together.

This example code:
- Extract *Buzzword hits* from *User Prompt* using the LLM predefined Chat Prompt template. *Bingo threshold* is set to 5.
- Implement a simple way of *Memory* (*State table*) storing previous sessions.
- How to integrate the *LangFuse* *CallbackHandler* and *get_client* and *propagate_attributes*.

Buzzword Bingo is just a silly example, but it showns how simple you can use *LangChain*, *LangGraph* and *LangFuse* with a local *Ollama* Stack.

## Try out the agent code sample

This will run various *Bingo sessions* and will create a `bingo:true` or `bingo:false` result.

```
uv run --env-file .env .\agents\meetup-bingo-agent.py
```

Take a look at your *LangFuse* environment if *traces* are shown.

- Inspect the *Tracing*.
- Validate which Bingo sessions succeeded and where Bingo!.
- Try to identify the *User Prompt*.
- Which metadata is logged.


## Try out the interactive code sample

This time you can try-out yourself, providing the *user Prompt*. Here the threshold is set to 2.

Just ask the question : *Does this session about AI Observability contain enough Buzzword Bingo?*

```
uv run --env-file .env .\agents\meetup-bingo-interactive.py
```

Following interactive console is opened.

```
Buzzword Bingo — type 'exit' to quit.
Session: meetup_bingo_console | Threshold: 2

> Does this session about AI Observability contain enough Buzzword Bingo?
```

Result you get is:

```
Hits (2): ['AI', 'Observability'] | Bingo: True
BINGO! 🎉 Keep going or 'exit'.
```

Why does the output, when Bingo, stay `deterministic` ?

Take a look at your *LangFuse* environment if *traces* are shown.

- Inspect the *Tracing*.
- Validate which Bingo sessions succeeded and where Bingo!.
- Try to identify the *User Prompt*.
- Which metadata is logged.

# Tools demo exercise

This exercise will introduce the usage of *Tools*. Again you will work with both the `agent` and `interactive` version of demo snippet. Here you will get some idea how *LangChain*, *LangGraph* and *LangFuse* work together.

This example code:
- This is a way to implement easy [add, multiply] and more complex 'square' calculations.
- You implement prefined logic using *Tools*.
- Introduce the *System Prompt*, which will be passed with the *User Prompt*.

Again silly example, but does the job explaning the implementation of using *Tools*.

## Try out the agent code sample

```
uv run --env-file .env .\agents\tools-demo-agent.py
```

The User Prompt is set to **"what is 250 + 250 + 500 + 1 * 5?"**.

What is the correct answer?

You may see that no *LangFuse* has been implemented yet. With the *examples* try to implement Observability using the *CallbackHandler*, *get_client* and *propagate_attributes* functions.

If you successfully integrated *LangFuse* you can take a look at your *LangFuse* environment if *traces* are shown.

- Inspect the *Tracing*.
- Validate if you can find the *System Prompt*.
- Try to identify the *User Prompt*.
- Which metadata is logged.

## Try out the interactive code sample

This time we can try it again ourselves. Let's challenge the LLM with a slidely different *User Prompt*.

**"what is (250 + 250 + 500 + 1) * 5?"**

Let's find out if the answer keeps the same. What do you think?

```
uv run --env-file .env .\agents\tools-demo-interactive.py
```

Take a look at your *LangFuse* environment if *traces* are shown.

- Inspect the *Tracing*.
- Validate if you can find the *System Prompt*.
- Try to identify the *User Prompt*.
- Which metadata is logged.