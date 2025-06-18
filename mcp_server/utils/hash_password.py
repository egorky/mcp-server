import getpass
from werkzeug.security import generate_password_hash

def main():
    print("Password Hash Generator for MCP Server")
    password = getpass.getpass("Enter password to hash: ")
    password_confirm = getpass.getpass("Confirm password: ")

    if not password:
        print("Password cannot be empty.")
        return

    if password != password_confirm:
        print("Passwords do not match.")
        return

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    print("\nGenerated Password Hash:")
    print(hashed_password)
    print("\nAdd this to your config.yaml under web_auth.password_hash")

if __name__ == '__main__':
    main()
