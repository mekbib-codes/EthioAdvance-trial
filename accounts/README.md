# accounts App

## User Model Structure
- **Roles**: PARENT, CHILD, TUTOR, COMPANY
- **Core Fields**: email (login), role, personal info  
- **Validation**: Phone format, date of birth range  

## Admin Features
- Filter by role/status  
- Read-only audit timestamps  
- Secure permission handling  

## Testing
Run tests with:
```bash
python manage.py test accounts --verbosity=2