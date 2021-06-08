import argparse
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    op = parser.add_subparsers(dest="op", required=True)

    listen = op.add_parser("listen")
    lop = listen.add_subparsers(dest="listen_op", required=True)
    attach = lop.add_parser("attach")
    attach.add_argument("session", type=str)
    new = lop.add_parser("new")
    new.add_argument("session", type=str)
    cust = lop.add_parser("custom", help="dont foget `--` prefix")
    cust.add_argument("custom", type=str, nargs="+")

    return parser.parse_args()


def main():
    # pylint: disable=import-outside-toplevel
    from pytmux.sync import cli

    args = parse_args()

    cli.ensure_tmux_compatible()

    if args.op == "listen":
        if args.listen_op == "attach":
            tmux_args = ["attach-session", "-t", args.session]
        elif args.listen_op == "new":
            tmux_args = ["new-session", "-s", args.session]
        elif args.listen_op == "custom":
            tmux_args = args.custom
        else:
            raise SystemExit("unknown listen op")

        cli.listen_all_events(tmux_args)
    else:
        raise SystemExit("unknown op")


if __name__ == "__main__":
    logging.basicConfig(
        level="DEBUG",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
        format="{asctime} {message}",
    )

    main()
