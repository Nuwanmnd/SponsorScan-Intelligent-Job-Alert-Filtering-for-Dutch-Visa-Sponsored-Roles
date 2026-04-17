
import os.path
import base64
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import datetime

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailClient:
    def __init__(self):
        self.creds = None
        self.service = None
        self.logger = logging.getLogger(__name__)

    def authenticate(self):
        """Authenticates with Gmail API."""
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    self.logger.error("credentials.json not found. Please provide it.")
                    print("ERROR: credentials.json not found. Please place it in the project directory.")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
            return True
        except Exception as e:
            self.logger.error(f"Failed to build Gmail service: {e}")
            return False

    def get_messages(self, sender='jobalerts-noreply@linkedin.com', days=3):
        """Fetches emails from a specific sender within the last N days."""
        if not self.service:
            self.logger.error("Gmail service not authenticated.")
            return []

        # Calculate date for query
        date_after = (datetime.date.today() - datetime.timedelta(days=days)).strftime('%Y/%m/%d')
        query = f'from:{sender} after:{date_after}'
        
        self.logger.info(f"Searching for emails with query: {query}")
        
        try:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=500).execute()
            messages = results.get('messages', [])
            return messages
        except Exception as e:
            self.logger.error(f"Failed to list messages: {e}")
            return []

    def get_message_detail(self, msg_id):
        """Fetches full message detail."""
        try:
            message = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            return message
        except Exception as e:
            self.logger.error(f"Failed to get message {msg_id}: {e}")
            return None

    def parse_message(self, message):
        """Parses email content to extract potential job/company info.
        Returns a list of (job_title, company, location) tuples.
        """
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = ""
        for h in headers:
            if h['name'] == 'Subject':
                subject = h['value']
                break
        
        # LinkedIn alerts usually contain multiple jobs.
        # We need to parse the HTML body.
        parts = payload.get('parts', [])
        body_data = None
        
        if 'body' in payload and payload['body'].get('data'):
             body_data = payload['body']['data']
             self.logger.info("DEBUG: Found body data in payload['body']")
        else:
            self.logger.info(f"DEBUG: No body in payload. Parts count: {len(parts)}")
            for part in parts:
                self.logger.info(f"DEBUG: Part mimeType: {part.get('mimeType')}")
                if part['mimeType'] == 'text/html':
                    body_data = part['body'].get('data')
                    self.logger.info("DEBUG: Found text/html part.")
                    break
        
        if not body_data:
            self.logger.warning("DEBUG: No body_data found in email.")
            return []

        html_content = base64.urlsafe_b64decode(body_data).decode('utf-8')
        self.logger.info(f"DEBUG: Decoded HTML content length: {len(html_content)}")
        soup = BeautifulSoup(html_content, 'html.parser')

        jobs = []
        
        # Strategy:
        # Traverse the HTML elements in order.
        # Capturing text from blocks and hrefs from <a> tags.
        
        final_items = []
        ignore_words = ["view job", "linkedin", "unsubscribe", "help", "app", "new jobs", "apply", "ago", "alert", "match", "see all jobs"]
        
        # We look into the body and iterate over all elements that might contain text
        # Using soup.descendants or just iterating over common tags can work.
        # But a simple way to preserve order and capture links is to iterate over tags.
        
        # Actually, soup.get_text() with separator is good for lines, but we lose links.
        # Let's iterate through the soup and find strings and links.
        
        for element in soup.descendants:
            if element.name == 'a':
                text = element.get_text(separator=' ').strip()
                href = element.get('href')
                
                if text and len(text) >= 2 and len(text) <= 100:
                    if not any(w in text.lower() for w in ignore_words):
                        final_items.append({
                            'text': text.replace('\u034f', ''),
                            'link': href,
                            'type': 'link_candidate'
                        })
            elif isinstance(element, str):
                parent = element.parent
                if parent.name not in ['a', 'script', 'style']:
                    text = element.strip()
                    if text and len(text) >= 2 and len(text) <= 100:
                        if not any(w in text.lower() for w in ignore_words):
                            final_items.append({
                                'text': text.replace('\u034f', ''),
                                'link': None,
                                'type': 'text'
                            })
                            
        return final_items

