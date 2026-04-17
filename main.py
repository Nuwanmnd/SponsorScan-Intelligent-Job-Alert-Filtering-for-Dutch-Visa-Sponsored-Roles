
import logging
from gmail_client import GmailClient
from sponsor_checker import SponsorChecker
from notifier import send_notification
from utils import setup_logging
import sys
import datetime
import os

def run_collection():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Gmail Job Alert Collection...")

    # 1. Initialize Components
    sponsor_checker = SponsorChecker()
    gmail_client = GmailClient()

    # 2. Fetch Sponsor List
    logger.info("Fetching sponsor list...")
    sponsor_checker.fetch_sponsor_list()
    if not sponsor_checker.sponsors:
        logger.error("No sponsors loaded. Exiting.")
        send_notification("Gmail Job Alert Error", "Failed to load sponsor list. Check logs.")
        return

    # 3. Authenticate Gmail
    logger.info("Authenticating with Gmail...")
    if not gmail_client.authenticate():
        logger.error("Gmail authentication failed.")
        send_notification("Gmail Job Alert Error", "Gmail authentication failed.")
        return

    # 4. Get Emails
    logger.info("Checking emails...")
    messages = gmail_client.get_messages(days=7) # Past 7 days as requested
    logger.info(f"Found {len(messages)} emails.")

    if not messages:
        logger.info("No recent job alert emails found.")
        return

    # 5. Process Emails
    from database import SessionLocal, Job
    session = SessionLocal()
    
    new_matches = []
    
    # OUTPUT FILE (Keep CSV for backup/legacy if user wants, or just rely on DB)
    # User requested database validation. Let's write to DB.
    
    # Load history from DB to prevent duplicates
    # We check (company, title)
    try:
        # Get all recent jobs to build local history cache
        # Optimization: only fetch last 30 days?
        cutoff = datetime.date.today() - datetime.timedelta(days=30)
        recent_jobs = session.query(Job).filter(Job.date_found >= cutoff).all()
        history = {(j.company.lower().strip(), j.title.lower().strip()) for j in recent_jobs}
        logger.info(f"Loaded {len(history)} recent matches from DB for deduplication.")
    except Exception as e:
        logger.error(f"Failed to load history from DB: {e}")

    for msg_meta in messages:
        msg_id = msg_meta['id']
        message = gmail_client.get_message_detail(msg_id)
        if not message:
            continue
            
        # Returns list of dicts: {'text': str, 'link': str/None, 'type': str}
        potential_items = gmail_client.parse_message(message)
        
        for i, item in enumerate(potential_items):
            text = item['text']
            link = item.get('link')
            
            # 1. Check if text matches a sponsor
            # The 'text' can be "Company Name" OR "Job Title" depending on parsing accuracy.
            # If it's a "Link Candidate" from <a> tag, it's likely "Job Title" but might contain Company.
            # The check_company matches against the sponsor list.
            
            # Scenario A: checking the text itself (common if text is just "Shell")
            is_sponsor = sponsor_checker.check_company(text)
            
            # Scenario B: Context based. 
            # If item is "Link Candidate" (Job Title), maybe the NEXT line is Company?
            # Or if text is Company, maybe PREVIOUS line is Job Title?
            
            match_found = False
            company_name = text
            job_title = "Unknown Job"
            
            # Heuristic 1: Current line is Company
            if is_sponsor:
                match_found = True
                company_name = text
                # Try to find title
                # If current item is a link, maybe it's "Company Name" link?
                # Look at previous line for Title?
                if i > 0:
                    job_title = potential_items[i-1]['text']
                    # If we found a title, check if it has a link
                    if potential_items[i-1].get('link'):
                        link = potential_items[i-1].get('link')
            
            # Heuristic 2: Current line is Job Title (has link), verify against items nearby for Company
            # This is harder without NER. 
            # But let's stick to the trusted "Sponsor Checker" logic.
            # If the Text IS the sponsor name, we flag it.
            
            if match_found:
                 # 3. INTERNSHIP FILTER
                ignore_keywords = ['intern', 'internship', 'stage', 'afstudeer', 'thesis', 'graduation']
                full_text_check = (company_name + " " + job_title).lower()
                
                if any(kw in full_text_check for kw in ignore_keywords):
                    logger.info(f"Skipping Internship/Thesis: {company_name} | {job_title}")
                    continue

                # 4. DUPLICATE CHECK
                clean_comp = company_name.strip()
                clean_title = job_title.strip()
                
                start_check = (clean_comp.lower(), clean_title.lower())
                if start_check in history:
                    logger.info(f"Skipping Duplicate (Found in DB): {clean_comp} | {clean_title}")
                    continue

                # It's a match!
                logger.info(f"MATCH FOUND: {company_name} (Title: {job_title}) - Link: {link}")
                new_matches.append({
                    'company': company_name,
                    'title': job_title,
                    'link': link
                })
                
                # Add to history immediately
                history.add(start_check)
                
                # 5. Save to DB
                try:
                    new_job = Job(
                        title=clean_title,
                        company=clean_comp,
                        link=link,
                        date_found=datetime.date.today(),
                        status='pending',
                        email_id=msg_id
                    )
                    session.add(new_job)
                    session.commit()
                    logger.info("Saved to SQLite.")
                except Exception as e:
                    logger.error(f"Failed to write to DB: {e}")
                    session.rollback()
                
                # 5. Save to CSV (Legacy Support/Backup)
                # ... skipping CSV ...
                
    session.close()

    # 6. Notify and Report
    if new_matches:
        # Deduplicate structured matches
        seen = set()
        unique_matches = []
        for m in new_matches:
            key = (m['company'].lower(), m['title'].lower())
            if key not in seen:
                seen.add(key)
                unique_matches.append(m)
                
        count = len(unique_matches)
        
        print("\n" + "="*40)
        print(f"FOUND {count} SPONSORED JOBS")
        print("="*40)
        for m in unique_matches:
            print(f"- {m['company']}: {m['title']}")
            if m['link']:
                print(f"  Link: {m['link']}")
        print("="*40)
        print(f"Details saved to SQLite Database (jobs.db)")
        
        title = f"Found {count} Sponsored Jobs!"
        body = "\n".join([f"{m['company']}: {m['title']}" for m in unique_matches[:3]])
        # Windows notifications have character limits (typically 256 for the balloon tip in plyer)
        if len(body) > 200:
            body = body[:197] + "..."
            
        # SUMMARY FILE
        SUMMARY_FILE = "summary.txt"
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            f.write(f"GMAIL ALERT - SPONSORED JOBS FOUND ({datetime.date.today()})\n")
            f.write("="*50 + "\n\n")
            for i, m in enumerate(unique_matches, 1):
                f.write(f"{i}. {m['company']} - {m['title']}\n")
                if m['link']:
                    f.write(f"   Link: {m['link']}\n")
                f.write("\n")
            f.write("="*50 + "\n")
            f.write(f"All records saved to SQLite Database (jobs.db)\n")
            
        # Open the summary file automatically
        try:
            os.startfile(SUMMARY_FILE)
        except Exception as e:
            logger.error(f"Failed to open summary file: {e}")

        send_notification(title, body)
        logger.info(f"Notification sent for: {unique_matches}")
    else:
        logger.info("No matching sponsored companies found (after filtering).")
        print("No matching sponsored jobs found.")

if __name__ == "__main__":
    run_collection()
