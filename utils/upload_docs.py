import os
import paramiko
import argparse
import stat


def locate_documentation_files(root_path):
    if not os.path.exists(os.path.join(root_path, "index.html")):
        raise FileNotFoundError(f"No index.html found in {root_path}")
    for root, dirs, files in os.walk(root_path):
        for f in files:
            yield os.path.relpath(root, root_path), f


def get_arg_parser():
    parser = argparse.ArgumentParser(description="Upload documentation")

    parser.add_argument(
        "source_dir",
        help="Root directory that contains the documentation rendered as html"
    )

    parser.add_argument(
        "host",
        help="Root directory that contains the documentation rendered as html"
    )

    parser.add_argument("--port", default=22)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--server_output", default='/var/www/html/dccdocs')
    parser.add_argument("--subroute", help="Subdirectory to deploy files to")

    return parser


def remove_files_from_directory(client: paramiko.SFTPClient, root):
    for i in client.listdir_attr(root):
        server_path = os.path.join(root, i.filename)
        if stat.S_ISDIR(i.st_mode):
            remove_files_from_directory(client, server_path)
        elif stat.S_ISREG(i.st_mode):
            client.remove(server_path)
        else:
            raise RuntimeError(
                f"Don't know what to do with {server_path}"
            )
        print(f"Removed {server_path}")
    client.rmdir(root)
    print(f"Removed {root}")


def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    with paramiko.Transport((args.host, args.port)) as transport:
        transport.connect(None, args.username, args.password)

        with paramiko.SFTPClient.from_transport(transport) as sftp:
            temp_dir = f"{args.subroute}.new"
            old_dir = f"{args.subroute}.old"

            output_directory = os.path.join(args.server_output, args.subroute)
            output_directory_tmp = os.path.join(args.server_output, temp_dir)

            # location to rename the file while working
            old_directory = os.path.join(
                args.server_output, old_dir
            )

            # Remove any temp directory
            if temp_dir in sftp.listdir(args.server_output):
                print(f"Found {temp_dir}. Removing")
                remove_files_from_directory(sftp, output_directory_tmp)

            if old_dir in sftp.listdir(args.server_output):
                print(f"Found {old_dir}. Removing")
                remove_files_from_directory(sftp, old_directory)

            # Copy data over to new tmp directory with .new suffix
            try:
                sftp.mkdir(output_directory_tmp)
                print("Uploading new data")
                sftp.chdir(output_directory_tmp)

                for subdir, file_name in locate_documentation_files(
                        args.source_dir
                ):
                    output = os.path.join(subdir, file_name)
                    print(output)
                    try:
                        sftp.stat(subdir)
                    except FileNotFoundError:
                        sftp.mkdir(subdir)

                    sftp.put(
                        os.path.join(args.source_dir, subdir, file_name),
                        output
                    )

            except OSError:
                remove_files_from_directory(sftp, output_directory_tmp)
                raise

            # swap the existing version with the new version
            if args.subroute in sftp.listdir(args.server_output):
                print(f"Renaming {output_directory} to {old_directory}")
                sftp.rename(output_directory, old_directory)

            print(f"Renaming {output_directory_tmp} to {output_directory}")
            sftp.rename(output_directory_tmp, output_directory)

            print("Successfully deployed")

            # When new data is has the final filename, Remove old version
            if old_dir in sftp.listdir(args.server_output):
                print(f"cleaning up {old_dir}.")
                remove_files_from_directory(sftp, old_directory)

if __name__ == '__main__':
    main()
