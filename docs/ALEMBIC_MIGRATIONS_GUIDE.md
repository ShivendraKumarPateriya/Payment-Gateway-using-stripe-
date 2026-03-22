# Alembic Database Migrations Guide

This guide explains how to use Alembic for managing database schema changes across your team.

## What is Alembic?

Alembic is a lightweight database migration tool that:
- ✅ Tracks all schema changes with version history
- ✅ Allows you to migrate forward/backward between database versions
- ✅ Makes it easy to coordinate schema changes across the team
- ✅ Keeps database schema in sync across all environments (dev, staging, prod)

## Quick Reference

| Task | Command |
|------|---------|
| **First-time setup** | `alembic upgrade head` |
| **Apply pending migrations** | `alembic upgrade head` |
| **Undo last migration** | `alembic downgrade -1` |
| **View migration history** | `alembic history` |
| **Check current version** | `alembic current` |
| **Generate migration (after model change)** | `alembic revision --autogenerate -m "description"` |

---

## Setup Instructions

### For New Team Members

When you first clone the repository:

```bash
# 1. Activate virtual environment
source myenv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create tables from existing migrations
alembic upgrade head

# ✅ Done! Your database now has all tables
```

After this, your database will have:
- `orders` table (stores payment orders)
- `stripe_webhook_events` table (stores webhook audit log)
- `alembic_version` table (tracks migration history)

---

## Making Database Schema Changes

### Step 1: Modify the Model

Edit `backend/app/db/models.py` to add/change a field:

```python
class Order(Base):
    """Represents one checkout order persisted before Stripe redirect."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # ... existing fields ...
    
    # NEW FIELD: Add discount tracking
    discount_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

### Step 2: Generate Migration

Alembic will auto-detect your changes:

```bash
source myenv/bin/activate
alembic revision --autogenerate -m "Add discount_percentage to orders"
```

This creates a new file:
```
alembic/versions/xxx_add_discount_percentage_to_orders.py
```

### Step 3: Review Generated Migration

The migration file contains the SQL changes. Review it to make sure it looks correct:

```python
# Check alembic/versions/xxx_add_discount_percentage_to_orders.py
def upgrade() -> None:
    # This is the "forward" migration
    op.add_column("orders", sa.Column("discount_percentage", sa.Integer(), nullable=True))

def downgrade() -> None:
    # This is the "reverse" migration (undo)
    op.drop_column("orders", "discount_percentage")
```

### Step 4: Apply Migration

```bash
alembic upgrade head
```

### Step 5: Commit & Push

```bash
git add backend/app/db/models.py alembic/versions/xxx_add_discount_percentage_to_orders.py
git commit -m "feat: add discount tracking to orders table

- Add discount_percentage field to Order model
- Create Alembic migration for schema update"
git push
```

---

## Team Workflow

### Person A: Makes a Database Change

```bash
# 1. Edit model
nano backend/app/db/models.py

# 2. Generate migration
alembic revision --autogenerate -m "Add refund_status to orders"

# 3. Review the generated file
cat alembic/versions/xxx_add_refund_status_to_orders.py

# 4. Apply it locally to test
alembic upgrade head

# 5. Commit & push
git add backend/app/db/models.py alembic/versions/xxx_add_refund_status_to_orders.py
git commit -m "feat: add refund_status to orders"
git push
```

### Person B: Gets the Changes

```bash
# 1. Pull latest code
git pull

# 2. Apply new migrations
alembic upgrade head

# ✅ Done! Their database now matches Person A's schema
```

---

## Understanding Migration Files

Here's what a migration file looks like:

```python
"""Add refund_status to orders.

Revision ID: abc123def456
Revises: xyz789
Create Date: 2025-03-22 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# unique identifier for this migration
revision = 'abc123def456'
down_revision = 'xyz789'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Apply this migration (moving forward in time)."""
    op.add_column('orders', sa.Column('refund_status', sa.String(32), nullable=True))

def downgrade() -> None:
    """Reverse this migration (moving backward in time)."""
    op.drop_column('orders', 'refund_status')
```

**Key fields:**
- `revision`: Unique ID for this migration
- `down_revision`: What this migration depends on
- `upgrade()`: SQL operations to move forward
- `downgrade()`: SQL operations to move backward

---

## Common Scenarios

### Scenario 1: Undo Last Migration

```bash
alembic downgrade -1
```

This runs the `downgrade()` function from the last migration.

### Scenario 2: See Migration History

```bash
alembic history
```

Output:
```
<base> -> c4d8cc52f45e (head), Initial migration with orders and webhook events
```

### Scenario 3: Check Current Database Version

```bash
alembic current
```

Output:
```
c4d8cc52f45e
```

### Scenario 4: Multiple Migrations Pending

If Person A created 3 new migrations and you pull them:

```bash
git pull
alembic upgrade head
```

This applies **all 3 migrations in order**.

### Scenario 5: Migrate to Specific Version

```bash
# Go to a specific migration (not usually needed)
alembic upgrade c4d8cc52f45e

# Go back N migrations
alembic downgrade -2  # goes back 2 migrations
```

---

## Sharing Database Across Team (Multi-Person Development)

### Setup PostgreSQL Server Once

```bash
# Option 1: Local Network (share one machine)
# Install PostgreSQL on Person A's machine, others connect remotely

# Option 2: Cloud (AWS RDS, Railway, Render)
# Create database in cloud, all team members connect to same server
```

### Update `.env` for All Team Members

```bash
# .env (everyone uses same DATABASE_URL)
DATABASE_URL=postgresql://user:password@shared_host:5432/stripe_payments
```

### Apply Migrations

```bash
# Each person:
source myenv/bin/activate
alembic upgrade head

# Everyone now has identical database schema!
```

---

## Important Guidelines

### ✅ DO:
- ✅ Run `alembic upgrade head` after pulling from git
- ✅ Generate migrations when you change models: `alembic revision --autogenerate`
- ✅ Review generated migration files before committing
- ✅ Commit both the model change AND the migration file
- ✅ Push migrations to GitHub for team coordination

### ❌ DON'T:
- ❌ Edit Alembic migration files manually (let autogenerate do it)
- ❌ Delete migration files after committing
- ❌ Skip running `alembic upgrade head` after pulling
- ❌ Use `Base.metadata.create_all()` in production (use migrations!)
- ❌ Edit migrations that other team members have already applied

---

## Troubleshooting

### Problem: "Can't find module backend.app.db"

**Solution:** Make sure you're in the project root directory:
```bash
cd /home/shivendra/Payment-Gateway-using-stripe-
source myenv/bin/activate
alembic revision --autogenerate -m "..."
```

### Problem: "Missing required environment variable: STRIPE_SECRET_KEY"

**Solution:** Make sure `.env` file exists in project root:
```bash
cp docs/example.env .env
# Edit .env with your Stripe keys
alembic revision --autogenerate -m "..."
```

### Problem: "No changes detected in schema"

**Solution:** You may have already applied that migration:
```bash
alembic current  # Check what version you're on
alembic history  # See all migrations
```

### Problem: "Can't migrate down - dependent migrations exist"

**Solution:** You can't delete a migration that others depend on:
```bash
# Just leave it as-is
# OR undo all migrations and start over (dev only!)
alembic downgrade base
```

---

## Next Steps

1. **First time?** Run: `alembic upgrade head`
2. **Making changes?** Follow "Making Database Schema Changes" section above
3. **New team member?** Run the "For New Team Members" setup
4. **Questions?** Check the troubleshooting section

---

## Related Documentation

- **Database Models:** [backend/app/db/models.py](../backend/app/db/models.py)
- **Alembic Official Docs:** [alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/)
- **Team Database Setup:** [docs/DATABASE_TEAM_SETUP.md](./DATABASE_TEAM_SETUP.md)
