# file: https://github.com/generative-computing/mellea/blob/main/docs/examples/instruct_validate_repair/101_email_with_validate.py
from mellea import MelleaSession
from mellea.backends.types import ModelOption
from mellea.backends.ollama import OllamaModelBackend
from mellea.backends import model_ids
from mellea.stdlib.sampling import RejectionSamplingStrategy

# create a session with Mistral running on Ollama
m = MelleaSession(
    backend=OllamaModelBackend(
        model_id=model_ids.MISTRALAI_MISTRAL_0_3_7B,
        model_options={ModelOption.MAX_NEW_TOKENS: 300},
    )
)

# run an instruction with requirements
email_v1 = m.instruct(
    "Write an email to invite all interns to the office party.",
    requirements=["be formal", "Use 'Dear interns' as greeting."],
    strategy=RejectionSamplingStrategy(loop_budget=3),
)

# print result
print(f"***** email ****\n{str(email_v1)}\n*******")
