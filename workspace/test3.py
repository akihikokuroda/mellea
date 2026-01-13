# file: https://github.com/generative-computing/mellea/blob/main/docs/examples/tutorial/simple_email.py#L1-L8
import mellea

# INFO: this line will download IBM's Granite 4 Micro 3B model.
m = mellea.start_session()

email = m.instruct("Write an email inviting interns to an office party at 3:30pm.")
print(str(email))
