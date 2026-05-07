from llm_sdk import Small_LLM_Model


def test():
    tes = Small_LLM_Model()
    string = "how old are you ?"
    encoded = tes.encode(string).tolist()[0]
    # encoded = encoded[0]
    while True:
        tokens = tes.get_logits_from_input_ids(encoded)
        new_token = tokens.index(max(tokens))
        encoded.append(new_token)
        print(tes.decode([new_token]), end="")


if __name__ == "__main__":
    try:
        test()
    except KeyboardInterrupt:
        pass
