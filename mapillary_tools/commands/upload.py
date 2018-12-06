import inspect
from mapillary_tools.upload import upload
from mapillary_tools.post_process import post_process
import os
from mapillary_tools import processing


class Command:
    name = 'upload'
    help = "Main tool : Upload images to Mapillary."

    def add_basic_arguments(self, parser):

        # command specific args
        parser.add_argument(
            '--skip_subfolders', help='Skip all subfolders and import only the images in the given directory path.', action='store_true', default=False, required=False)

    def add_advanced_arguments(self, parser):
        parser.add_argument(
            '--number_threads', help='Specify the number of upload threads.', type=int, default=None, required=False)
        parser.add_argument(
            '--max_attempts', help='Specify the maximum number of attempts to upload.', type=int, default=None, required=False)

        # post process
        parser.add_argument('--summarize', help='Summarize import for given import path.',
                            action='store_true', default=False, required=False)
        parser.add_argument('--move_images', help='Move images corresponding to sequence uuid, duplicate flag and upload status.',
                            action='store_true', default=False, required=False)
        parser.add_argument('--save_as_json', help='Save summary or file status list in a json.',
                            action='store_true', default=False, required=False)
        parser.add_argument('--list_file_status', help='List file status for given import path.',
                            action='store_true', default=False, required=False)
        parser.add_argument('--push_images', help='Push images uploaded in given import path.',
                            action='store_true', default=False, required=False)
        parser.add_argument('--save_local_mapping', help='Save the mapillary photo uuid to local file mapping in a csv.',
                            action='store_true', default=False, required=False)

    def run(self, args):

        vars_args = vars(args)
        log_counts_path = os.path.join(
            vars_args["import_path"], "mapillary_tools_progress_counts.json")
        if os.path.isfile(log_counts_path):
            log_counts_ = processing.load_json(log_counts_path)
            if vars_args["rerun"]:
                total_uploaded = 0
                if "upload_summary" in log_counts_:
                    if "finalized" in log_counts_["upload_summary"]:
                        total_uploaded = log_counts_[
                            "upload_summary"]["finalized"]
                    elif "upload" in log_counts_["upload_summary"] and "success" in log_counts_["upload_summary"]["upload"]:
                        total_uploaded = log_counts_[
                            "upload_summary"]["upload"]["success"]
                if "process_summary" in log_counts_:
                    for process_step in log_counts_["process_summary"]:
                        if process_step == "duplicates":
                            del log_counts_["process_summary"][process_step]
                        elif "failed" in log_counts_["process_summary"][process_step]:
                            del log_counts_[
                                "process_summary"][process_step]["failed"]
                        elif "success" in log_counts_["process_summary"][process_step]:
                            log_counts_[
                                "process_summary"][process_step]["success"] = total_uploaded
                    processing.log_counts = log_counts_

            else:
                if "process_summary" in log_counts_:
                    for process_step in log_counts_["process_summary"]:
                        if process_step != "duplicates" and "failed" in log_counts_["process_summary"][process_step]:
                            del log_counts_[
                                "process_summary"][process_step]["failed"]
                    processing.log_counts = log_counts_

        upload(**({k: v for k, v in vars_args.iteritems()
                   if k in inspect.getargspec(upload).args}))

        post_process(**({k: v for k, v in vars_args.iteritems()
                         if k in inspect.getargspec(post_process).args}))
        if not "total_images" in processing.log_counts:
            processing.log_counts["total_images"] = processing.total_files
        processing.save_json(processing.log_counts, os.path.join(
            vars_args["import_path"], "mapillary_tools_progress_counts.json"))
