# Driver onboarding

Restart the backend to create the new `driver_registrations` table through the existing startup table creation. Deployments managed with Alembic should run `alembic upgrade head` from `backend`.

Sign in to the Flutter application using an existing account whose role is `ADMIN`. This opens the Super Admin dashboard (the dashboard uses the existing ADMIN permission; it does not introduce a separate privilege tier).

1. Select **Create bus & route** and enter the registration plate, device identifier, and route/destinations, or use an existing bus.
2. Select **Create driver**. Enter name, phone, email, national ID, address, driving licence and login password.
3. Upload front and back ID photos as JPEG or PNG, up to 2 MB per photo.
4. Select the bus and route. A bus with an active driver cannot be assigned again through onboarding.
5. Enable **Driver has an assistant** if applicable, then complete the assistant's contact and identity fields and both ID photos.
6. Save. The driver can sign in using the entered email and password and accesses the assigned bus through the existing driver flow.

Tap a driver on the dashboard to review registration details. Only ADMIN accounts can access registration endpoints. Passwords are hashed; ID photos, residential address and assistant details are encrypted using the configured ENCRYPTION_KEY. Keep that key stable to retain access to saved documents. The list endpoint omits uploaded documents.

Driver onboarding endpoints:
- `GET /admin/driver-registrations`
- `POST /admin/driver-registrations`
- `GET /admin/driver-registrations/{driver_id}`
