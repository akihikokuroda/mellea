# file: https://github.com/generative-computing/mellea/blob/main/docs/examples/tutorial/simple_email.py#L13-L27
import mellea

def write_email(m: mellea.MelleaSession, name: str, notes: str) -> str:
  email = m.instruct(
    "Write an email to {{name}} using the notes following: {{notes}}.",
    user_variables={"name": name, "notes": notes},
  )
  return email.value  # str(email) also works.

m = mellea.start_session()
print(write_email(m, "Olivia",
                  "Olivia helped the lab over the last few weeks by organizing intern events, advertising the speaker series, and handling issues with snack delivery."))
