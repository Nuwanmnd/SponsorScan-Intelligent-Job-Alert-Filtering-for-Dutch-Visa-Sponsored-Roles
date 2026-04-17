You are helping me tailor my CV for a specific job.

Below is my base CV content. It is NOT perfectly general, so your task is to intelligently adapt it to the job description I provide.

Your job:

1. Analyze the job description against my CV.
2. Decide what parts of my CV are most relevant.
3. Rewrite the CV so it is targeted to the role.
4. Keep the final CV suitable for a ONE-PAGE layout.
5. Prioritize the strongest and most relevant information first.
6. Remove repetition, weak points, and low-value details if space is tight.
7. Do not invent experience, tools, or responsibilities I do not actually have.
8. If the role is a weak fit, still suggest the best possible angle, but clearly avoid exaggeration.

Important formatting and decision rules:

- Always optimize for recruiter readability in the first 6-10 seconds.
- The title and profile summary must match the role directly.
- Keep the most job-relevant achievements and tools.
- Prefer practical, concrete bullets over abstract statements.
- If two bullets say similar things, merge or remove one.
- Keep the CV concise enough for one page.
- If space is limited, remove less relevant items in this order:
  1. Kaggle
  2. older freelance design/web work details
  3. one or two lower-value education bullets
  4. extra project bullets
- Do not remove the strongest matching project if it is relevant to the role.
- Keep the tone human, professional, and realistic.
- Avoid jargon overload and avoid sounding generic.

What I want as output:
A) Recommended CV Title
B) Recommended Profile Summary
C) Keep / Remove / Rewrite notes for each major section
D) Final One-Page CV Draft split into named sections
E) Optional Extra Details = useful details that could be added only if there is space
F) What not to claim = tools/experience I should not pretend to have
G) Key points to highlight in the cover letter
H) Tailored cover letter

When tailoring the CV, think in this priority order:
1. Direct match to job requirements
2. Evidence of practical work
3. Relevant technical tools
4. Analytical/problem-solving ability
5. Communication/collaboration signals
6. Older or less relevant supporting details

Return valid JSON only. Do not wrap it in markdown fences.

Use this schema exactly:
{
  "recommended_cv_title": "short role-specific CV headline",
  "recommended_profile_summary": "a 3-5 sentence profile summary tailored to the role and grounded in the candidate's real background",
  "section_notes": {
    "skills": {
      "keep": ["items to keep in skills"],
      "remove": ["items to remove or reduce from skills"],
      "rewrite": ["how to rewrite or reorder the skills section"]
    },
    "projects": {
      "keep": ["items to keep in projects"],
      "remove": ["items to remove or reduce from projects"],
      "rewrite": ["how to rewrite the projects section"]
    },
    "experience": {
      "keep": ["items to keep in experience"],
      "remove": ["items to remove or reduce from experience"],
      "rewrite": ["how to rewrite the experience section"]
    },
    "education": {
      "keep": ["items to keep in education"],
      "remove": ["items to remove or reduce from education"],
      "rewrite": ["how to rewrite the education section"]
    },
    "general_structure": {
      "keep": ["overall structural choices to keep"],
      "remove": ["overall structural items to reduce or remove"],
      "rewrite": ["how to reorder the CV for one-page impact"]
    }
  },
  "final_one_page_cv_draft": {
    "title": "final CV headline",
    "profile_summary": "final tailored profile summary",
    "skills": ["skill grouping or skill lines as they should appear in the CV"],
    "experience": ["final experience bullets or compressed entries for the one-page CV"],
    "projects": ["final project bullets or compact project entries"],
    "education": ["final education lines or bullets"],
    "additional_sections": ["optional final lines for certifications, courses, or other short sections if still worth including"]
  },
  "optional_extra_details": [
    "useful details that can be added only if there is space"
  ],
  "what_not_to_claim": [
    "tools, responsibilities, or experience the candidate should not pretend to have"
  ],
  "key_points_to_highlight": [
    "point 1",
    "point 2",
    "point 3"
  ],
  "cover_letter": "full tailored cover letter text"
}

Rules:
- Keep all advice truthful and grounded in the provided CV and notes
- Do not invent achievements, employers, tools, or qualifications the candidate did not provide
- The final CV draft should read like a polished one-page CV, not like notes
- The structured final CV draft must be concise and ready to copy into a real CV layout
- The cover letter should sound professional, credible, and role-specific
- Favor truthful positioning over exaggerated claims
