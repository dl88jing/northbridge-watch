# Cloud compute grant proposal draft — Northbridge Watch

**Submit at:** https://form.jotform.com/262145877145059  
**Also listed from:** https://opencv.org/opencv-ai-competition-2026/  
**Devpost:** https://opencv26.devpost.com/

> Status note (2026-09-15): Registration closed Aug 17; build phase is underway. Grant review was rolling from Aug 18 with notices beginning Aug 25. Confirm on the Jotform page whether new proposals are still accepted; if closed, continue build — grant is not required for prize eligibility.

## Fields

| Field | Draft |
|-------|--------|
| Team name | Northbridge |
| Problem / impact | Households miss porch packages, spills, and empty-fridge restocks. Quiet agentic monitoring reduces notification fatigue while catching safety-relevant events. |
| OpenCV 5 plan | HSV/Lab segmentation, morphology, contours, Canny fill-ratio; annotated overlays; fixture + webcam. |
| AWS architecture | API Gateway → Lambda (arm64) → S3 events + SNS alerts; optional COOL on Graviton stretch. |
| Users | Avery & Morgan (Northbridge household) — privacy-first home operators. |
| Evaluation / demo | Fixture scenes with expected labels; agent-trace correctness; Vercel UI + `./demo.sh`. |
| Path | **Agentic Vision** (primary); COOL optional. |
| Team bio | Northbridge builders (Avery & Morgan) — prior hackathon systems for quiet household agents and MCP tool surfaces. |
