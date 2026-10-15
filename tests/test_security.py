import os, unittest, base64, re
os.environ['DATABASE_URL']='sqlite:///:memory:'
os.environ['SECRET_KEY']='synthetic-test-signing-key'
os.environ['SESSION_COOKIE_SECURE']='false'
from app import app
from app.models import db, User

class SecurityTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, ADMIN_PASSWORD='synthetic-administrator-password')
        with app.app_context():
            db.drop_all(); db.create_all(); db.session.add(User(id=1,username='guest'));db.session.commit()
        self.client=app.test_client()
        with self.client.session_transaction() as s:s['user_id']=1;s['username']='guest'
    def auth(self):
        return {'Authorization':'Basic '+base64.b64encode(b'admin:synthetic-administrator-password').decode()}
    def test_guest_cannot_administer(self):
        self.assertEqual(self.client.get('/fill-db').status_code,401)
    def test_admin_can_open_import(self):
        self.assertEqual(self.client.get('/fill-db',headers=self.auth()).status_code,200)
    def test_admin_without_csrf_cannot_write(self):
        self.assertEqual(self.client.post('/confirm-fill-db',headers=self.auth()).status_code,400)
    def test_missing_configuration_fails_closed(self):
        app.config['ADMIN_PASSWORD']=''
        self.assertEqual(self.client.get('/fill-db').status_code,503)
    def test_rendered_import_has_valid_csrf(self):
        page=self.client.get('/fill-db',headers=self.auth()).get_data(as_text=True)
        token=re.search(r'name="csrf_token" value="([^" ]+)"',page).group(1)
        response=self.client.post('/fill-db',data={'csrf_token':token,'stage':'invalid'},headers=self.auth())
        self.assertEqual(response.status_code,302)

if __name__=='__main__':unittest.main()
