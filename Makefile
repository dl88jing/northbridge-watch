.PHONY: setup demo test eval baseline failures serve web deploy-web deploy-aws deck

setup:
	@test -d .venv || (python3 -m venv .venv && .venv/bin/pip install -q -U pip && .venv/bin/pip install -q -r requirements.txt pytest httpx && .venv/bin/pip install -q -e .)

demo: setup          ## one-command demo: regenerate fixtures, run the OpenCV 5 agent loop
	./demo.sh demo

test: setup
	.venv/bin/python -m pytest -q

eval: setup          ## held-out synthetic evaluation -> docs/eval/
	.venv/bin/python -m northbridge_watch.eval.run_eval

baseline: setup      ## same eval with the v1 detector (commit 2fe7893) -> docs/eval/baseline-v1/
	./scripts/eval_baseline_v1.sh

failures: setup      ## render failure cases -> docs/failures/
	.venv/bin/python scripts/make_failure_gallery.py

serve: setup
	./demo.sh serve

web:
	./demo.sh web

deploy-web:
	vercel deploy --prod --yes

deploy-aws:          ## needs AWS credentials + SAM CLI
	./scripts/deploy_aws.sh --wire-vercel

deck:                ## rebuild docs/pitch-deck.pdf from docs/deck/pitch-deck.html
	scripts/build_deck_pdf.sh
