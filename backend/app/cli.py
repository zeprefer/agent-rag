import argparse
import sys

from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.services.users import create_tenant, create_user, get_user_by_email


def create_admin(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        existing = get_user_by_email(db, args.email)
        if existing is not None:
            if args.if_not_exists:
                print(f"Admin user already exists: {args.email}")
                return 0
            print(f"User already exists: {args.email}", file=sys.stderr)
            return 1

        tenant = create_tenant(db, name=args.tenant_name)
        create_user(
            db,
            tenant=tenant,
            email=args.email,
            password=args.password,
            name=args.name,
            role="admin",
        )
        db.commit()
        print(f"Created admin {args.email} for tenant {args.tenant_name}")
        return 0
    except IntegrityError as exc:
        db.rollback()
        print(f"Could not create admin: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enterprise Agent RAG backend CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    admin_parser = subparsers.add_parser("create-admin", help="Create the first tenant administrator")
    admin_parser.add_argument("--email", required=True)
    admin_parser.add_argument("--password", required=True)
    admin_parser.add_argument("--tenant-name", required=True)
    admin_parser.add_argument("--name", default=None)
    admin_parser.add_argument("--if-not-exists", action="store_true")
    admin_parser.set_defaults(func=create_admin)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
