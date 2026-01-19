# 🔐 Auth Blueprint

## Panoramica

Il modulo Auth gestisce l'autenticazione, autorizzazione e gestione delle sessioni utente per Corposostenibile Suite. Include gestione password sicura con reset via email, sessioni persistenti e integrazione con Flask-Login.

## Funzionalità Principali

- **Login/Logout** tradizionale con email e password
- **OAuth2 Integration** con Google
- **Password Reset** via email con token sicuri
- **Remember Me** con cookie persistenti
- **Session Management** sicura
- **Permission System** basato su ruoli (ACL)
- **Password Security** con hashing bcrypt
- **Account Lockout** dopo tentativi falliti

## Struttura File

```
auth/
├── __init__.py          # Blueprint registration
├── routes.py            # Route handlers
├── forms.py             # WTForms per login/registrazione
├── email_utils.py       # Utility per invio email
├── cli.py               # Comandi CLI (create-admin)
└── templates/
    └── auth/
        ├── login.html           # Form login
        ├── forgot_password.html # Richiesta reset
        ├── reset_form.html      # Form nuovo password
        └── email/               # Template email
```

## Route Principali

| Route | Metodo | Descrizione | Autenticazione |
|-------|---------|-------------|----------------|
| `/auth/login` | GET/POST | Form login | No |
| `/auth/logout` | GET | Logout utente | Sì |
| `/auth/google` | GET | Inizio OAuth2 | No |
| `/auth/google/callback` | GET | Callback OAuth2 | No |
| `/auth/forgot-password` | GET/POST | Richiesta reset | No |
| `/auth/reset/<token>` | GET/POST | Reset password | No |

## Modelli Database

### User (in models.py)

```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    google_id = db.Column(db.String(100), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    last_login_at = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
```

## Form Disponibili

### LoginForm
- `email` - Email address (required, validated)
- `password` - Password (required, min 6 chars)
- `remember_me` - Checkbox per sessione persistente

### ForgotPasswordForm
- `email` - Email per reset link

### ResetPasswordForm
- `password` - Nuova password (min 8 chars)
- `password_confirm` - Conferma password

## Configurazione

### Variabili .env richieste

```bash
# Google OAuth2
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URL=http://localhost:5000/auth/google/callback

# Email per password reset
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Security
SECRET_KEY=your-secret-key-here
SESSION_COOKIE_SECURE=0  # 1 in production
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=300
```

## Utilizzo

### Login Standard

```python
# Nelle tue route
from flask_login import login_required, current_user

@app.route('/protected')
@login_required
def protected_route():
    return f"Ciao {current_user.email}!"
```

### Controllo Permessi

```python
# Decorator per permessi
from corposostenibile.decorators import requires_permission

@app.route('/admin')
@login_required
@requires_permission('admin.access')
def admin_panel():
    return render_template('admin/panel.html')
```

### Login Programmatico

```python
from flask_login import login_user
from corposostenibile.models import User

# Durante registrazione o altro
user = User(email='nuovo@example.com')
user.set_password('password123')
db.session.add(user)
db.session.commit()

# Login automatico
login_user(user, remember=True)
```

## Comandi CLI

```bash
# Crea utente admin
flask auth create-admin --email admin@example.com --password secret123

# Reset password utente
flask auth reset-password --email user@example.com

# Sblocca account
flask auth unlock-user --email user@example.com
```

## Security Best Practices

1. **Password Requirements**
   - Minimo 8 caratteri
   - Mix di maiuscole/minuscole
   - Almeno un numero
   - Caratteri speciali consigliati

2. **Session Security**
   - Cookie HTTPOnly
   - Secure flag in production
   - SameSite protection
   - Session timeout

3. **Account Protection**
   - Lockout dopo 5 tentativi
   - Captcha dopo 3 tentativi (TODO)
   - Email verification (TODO)
   - 2FA ready (TODO)

## Testing

```python
# tests/test_auth.py
def test_login(client):
    response = client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 302
    
def test_protected_route_requires_login(client):
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/auth/login' in response.location
```

## Troubleshooting

### "Invalid credentials"
- Verifica email corretta
- Password case-sensitive
- Account non bloccato
- Utente attivo nel DB

### Google OAuth non funziona
- Verifica GOOGLE_CLIENT_ID e SECRET
- Callback URL deve matchare esattamente
- Dominio autorizzato su Google Console

### Email reset non arriva
- Controlla configurazione SMTP
- Verifica spam folder
- Logs per errori invio

## Estensioni Future

- [ ] Two-Factor Authentication (2FA)
- [ ] Email verification obbligatoria
- [ ] Password complexity meter
- [ ] Login con Microsoft/GitHub
- [ ] Audit log accessi
- [ ] Remember device
- [ ] Biometric login support

## Contribuire

Per modifiche al modulo auth:
1. Aggiungi test per nuove funzionalità
2. Mantieni retrocompatibilità
3. Documenta nuove configurazioni
4. Aggiorna questo README

## Riferimenti

- [Flask-Login Docs](https://flask-login.readthedocs.io/)
- [OAuth2 Google Guide](https://developers.google.com/identity/protocols/oauth2)
- [OWASP Authentication](https://owasp.org/www-project-cheat-sheets/cheatsheets/Authentication_Cheat_Sheet)