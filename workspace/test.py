# file: https://github.com/generative-computing/mellea/blob/main/docs/examples/tutorial/example.py
import mellea

m = mellea.start_session()
print(m.chat("What is the etymology of mellea?").content)
