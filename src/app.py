import os
import streamlit as st
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime
from tmdbv3api import TMDb, TV, Search, Season
from dotenv import load_dotenv
import re
from pathlib import Path
import pandas as pd
import tempfile
import shutil

# Load environment variables
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="TV Show Renamer",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Material Design 3 inspired CSS
st.markdown(
    """
    <style>
    /* Material Design 3 Colors and Variables */
    :root {
        --md-sys-color-primary: #006399;
        --md-sys-color-on-primary: #ffffff;
        --md-sys-color-primary-container: #cde5ff;
        --md-sys-color-on-primary-container: #001d32;
        --md-sys-color-surface: #1c1b1f;
        --md-sys-color-on-surface: #e6e1e5;
        --md-sys-color-surface-variant: #44474a;
        --md-sys-color-outline: #8c9198;
    }
    
    /* Global Styles */
    .stApp {
        background-color: var(--md-sys-color-surface);
        color: var(--md-sys-color-on-surface);
    }
    
    /* Drop Zone */
    .drop-zone {
        border: 2px dashed var(--md-sys-color-outline);
        border-radius: 12px;
        padding: 40px;
        text-align: center;
        margin: 20px 0;
        background-color: var(--md-sys-color-surface-variant);
        cursor: pointer;
        min-height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        font-size: 1.2em;
    }
    
    .drop-zone:hover {
        border-color: var(--md-sys-color-primary);
        background-color: rgba(0, 99, 153, 0.1);
    }
    
    /* Hide default file uploader label */
    .stFileUploader label {
        display: none;
    }
    
    /* Data Table */
    .dataframe {
        background-color: var(--md-sys-color-surface-variant);
        border: 1px solid var(--md-sys-color-outline);
        border-radius: 4px;
        font-size: 14px;
        width: 100%;
        margin: 20px 0;
    }
    
    .dataframe th {
        background-color: var(--md-sys-color-surface-variant);
        color: var(--md-sys-color-on-surface);
        font-weight: 500;
        padding: 12px 16px;
        text-align: left;
        border-bottom: 1px solid var(--md-sys-color-outline);
    }
    
    .dataframe td {
        padding: 12px 16px;
        border-bottom: 1px solid var(--md-sys-color-outline);
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 20px;
        padding: 8px 24px;
        font-size: 14px;
        font-weight: 500;
        background-color: var(--md-sys-color-primary);
        color: var(--md-sys-color-on-primary);
        border: none;
        margin: 8px 0;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background-color: var(--md-sys-color-primary-container);
        color: var(--md-sys-color-on-primary-container);
    }
    
    /* Status */
    .status-ready {
        color: #4caf50;
    }
    .status-pending {
        color: #ffc107;
    }
    </style>
""",
    unsafe_allow_html=True,
)


class StreamlitTVShowRenamer:
    """Streamlit interface for TV show renaming."""

    def __init__(self):
        """Initialize the Streamlit TV show renamer."""
        # Initialize TMDb
        self.tmdb = TMDb()
        self.tmdb.api_key = os.getenv("TMDB_API_KEY")
        if not self.tmdb.api_key:
            st.error("TMDB API key not found. Please check your .env file.")
            return

        self.tv = TV()
        self.season_api = Season()

        # Initialize session state variables
        if "files" not in st.session_state:
            st.session_state.files = []
        if "renamed_files" not in st.session_state:
            st.session_state.renamed_files = {}
        if "selected_show" not in st.session_state:
            st.session_state.selected_show = None
        if "show_search_results" not in st.session_state:
            st.session_state.show_search_results = {}
        if "current_directory" not in st.session_state:
            st.session_state.current_directory = str(Path.home() / "Downloads")

    def search_tv_show(self, query: str) -> List[Dict]:
        """Search for TV shows using TMDB API and cache results."""
        try:
            # Check if we have cached results for this query
            cache_key = query.lower().strip()
            if cache_key in st.session_state.show_search_results:
                return st.session_state.show_search_results[cache_key]

            # Get search results
            shows = self.tv.search(query)
            results = []

            for show in shows:
                # Create a clean show object with essential info
                show_data = {
                    "id": show.id,
                    "name": show.name,
                    "first_air_date": getattr(show, "first_air_date", "N/A"),
                    "overview": (
                        getattr(show, "overview", "")
                        if hasattr(show, "overview")
                        else ""
                    ),
                    "original_name": getattr(show, "original_name", show.name),
                }

                # Format display name
                year = (
                    show_data["first_air_date"][:4]
                    if show_data["first_air_date"] != "N/A"
                    else "N/A"
                )
                show_data["display_name"] = f"{show_data['name']} ({year})"

                results.append(show_data)

            # Cache the results
            st.session_state.show_search_results[cache_key] = results
            return results

        except Exception as e:
            st.error(f"Error searching for shows: {str(e)}")
            return []

    def get_season_details(self, show_id: int, season_num: int):
        """Get detailed information about a specific season."""
        try:
            season_details = self.season_api.details(show_id, season_num)
            if not season_details:
                st.warning(f"No season found for show {show_id}, season {season_num}")
                return None
            return season_details
        except Exception as e:
            st.error(f"Error getting season details: {str(e)}")
            return None

    def select_tv_show(self):
        """Handle TV show selection and display season/episode selection."""
        if not st.session_state.files:
            return

        # Show search box
        query = st.text_input("Search for TV Show", key="show_search")

        if query:
            show_names = self.search_tv_show(query)
            if show_names:
                # Display show selection dropdown
                selected_show_name = st.selectbox(
                    "Select TV Show", [show["display_name"] for show in show_names]
                )

                if selected_show_name:
                    # Get the actual show object from our stored results
                    show = next(
                        (
                            show
                            for show in show_names
                            if show["display_name"] == selected_show_name
                        ),
                        None,
                    )
                    if show:
                        st.session_state.selected_show = show

                        # Add custom CSS for show details
                        st.markdown(
                            """
                            <style>
                                .show-details {
                                    background-color: #1e1e1e;
                                    border-radius: 10px;
                                    padding: 20px;
                                    margin: 20px 0;
                                }
                                .show-title {
                                    font-size: 24px;
                                    font-weight: bold;
                                    color: #ffffff;
                                    margin-bottom: 10px;
                                }
                                .show-meta {
                                    font-size: 14px;
                                    color: #888888;
                                    margin-bottom: 15px;
                                }
                                .show-overview {
                                    color: #dddddd;
                                    line-height: 1.6;
                                    padding: 10px 0;
                                    border-top: 1px solid #333333;
                                    max-height: none;
                                    overflow: visible;
                                    text-overflow: clip;
                                    white-space: normal;
                                }
                            </style>
                        """,
                            unsafe_allow_html=True,
                        )

                        # Show information with improved layout
                        st.markdown(
                            f"""
                            <div class="show-details">
                                <div class="show-title">{show['name']}</div>
                                <div class="show-meta">First Aired: {show['first_air_date']}</div>
                                <div class="show-overview">{show['overview']}</div>
                            </div>
                        """,
                            unsafe_allow_html=True,
                        )

                        # Add some spacing
                        st.markdown("<br>", unsafe_allow_html=True)

                        # Get show details for seasons
                        details = self.tv.details(show["id"])
                        if details and hasattr(details, "number_of_seasons"):
                            season_numbers = list(
                                range(1, details.number_of_seasons + 1)
                            )
                            selected_season = st.selectbox(
                                "Select Season",
                                season_numbers,
                                format_func=lambda x: f"Season {x}",
                            )

                            if selected_season:
                                # Get season details
                                season_details = self.get_season_details(
                                    show["id"], selected_season
                                )
                                if season_details and hasattr(
                                    season_details, "episodes"
                                ):
                                    # Process files for the selected show and season
                                    self.process_files_for_season(
                                        show["name"],
                                        show["id"],
                                        selected_season,
                                        season_details,
                                    )
                        else:
                            st.error("Could not fetch show details")
            else:
                st.warning("No shows found")

    def process_files_for_season(
        self, show_name: str, show_id: int, season: int, season_details
    ):
        """Process files for the selected show and season."""
        success_count = 0
        skipped_count = 0
        failed_count = 0

        with st.spinner("Processing files..."):
            for file in st.session_state.files:
                try:
                    show_info = self.extract_show_info(file["name"])
                    if not show_info:
                        failed_count += 1
                        continue

                    _, file_season, episode = show_info

                    # Skip files from different seasons
                    if file_season != season:
                        skipped_count += 1
                        continue

                    # Process files with matching season
                    matching_episode = next(
                        (
                            ep
                            for ep in season_details.episodes
                            if ep.episode_number == episode
                        ),
                        None,
                    )

                    if matching_episode:
                        extension = os.path.splitext(file["name"])[1]
                        new_name = f"{show_name}-S{season:02d}E{episode:02d}-{matching_episode.name}{extension}"
                        st.session_state.renamed_files[file["name"]] = new_name
                        success_count += 1
                    else:
                        failed_count += 1

                except Exception:
                    failed_count += 1

            # Show summary
            if success_count > 0:
                st.success(f"✓ Successfully matched {success_count} file(s)")
            if skipped_count > 0:
                st.info(f"↷ Skipped {skipped_count} file(s) from different seasons")
            if failed_count > 0:
                st.warning(f"⚠ Failed to match {failed_count} file(s)")

    def extract_show_info(self, filename: str) -> Optional[Tuple[str, int, int]]:
        """Extract show name, season number, and episode number from filename."""
        # Common patterns for TV show filenames
        patterns = [
            # [Tag]Show_-_01 (episode-only format)
            r"\[.*?\](.*?)[-_\s]*(\d{2,})",
            # Show.Name.S01E02 or Show.Name.S1E02
            r"(.*?)[\.\s][Ss](\d{1,2})[Ee](\d{1,2})",
            # Show.Name.1x02 or Show.Name.01x02
            r"(.*?)[\.\s](\d{1,2})x(\d{1,2})",
            # Show.Name.102 (where first digit is season, next two are episode)
            r"(.*?)[\.\s](\d{1})(\d{2})",
            # Show.Name.Season.1.Episode.02
            r"(.*?)[\.\s][Ss]eason[\.\s]?(\d{1,2})[\.\s][Ee]pisode[\.\s]?(\d{1,2})",
            # Show.Name.E02.S01
            r"(.*?)[\.\s][Ee](\d{1,2})[\.\s][Ss](\d{1,2})",
        ]

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                groups = match.groups()

                # Clean up show name
                show_name = groups[0]
                # Remove dots, underscores, brackets
                show_name = re.sub(r"[\._\[\]]", " ", show_name)
                # Remove multiple spaces and trim
                show_name = " ".join(show_name.split()).strip()

                if len(groups) == 2:  # Episode-only format
                    season = 1  # Default to season 1
                    episode = int(groups[1])
                elif len(groups) == 3:
                    if pattern == r"(.*?)[\.\s][Ee](\d{1,2})[\.\s][Ss](\d{1,2})":
                        # Handle E02.S01 format (episode before season)
                        season = int(groups[2])
                        episode = int(groups[1])
                    else:
                        season = int(groups[1])
                        episode = int(groups[2])

                return show_name, season, episode

        return None

    def display_drop_zone(self):
        """Display the file drop zone."""
        # Add custom styling for the file uploader
        st.markdown(
            """
            <style>
                /* Hide the file size limit message */
                .stFileUploader > div > small {
                    display: none;
                }
                
                .uploadedFile {
                    border: 2px dashed #4caf50;
                    border-radius: 12px;
                    padding: 30px;
                    text-align: center;
                    background-color: rgba(76, 175, 80, 0.1);
                }
                
                /* Make the upload area bigger */
                .stFileUploader > div > div {
                    min-height: 300px;
                    padding: 40px;
                    margin: 20px 0;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    background-color: #f8f9fa;
                    border: 3px dashed #ccc;
                    border-radius: 15px;
                    transition: all 0.3s ease;
                }
                
                .stFileUploader > div > div:hover {
                    border-color: #4caf50;
                    background-color: rgba(76, 175, 80, 0.1);
                    transform: scale(1.02);
                }
                
                .stFileUploader > div > div::before {
                    content: "📁";
                    font-size: 5em;
                    margin-bottom: 20px;
                }
                
                .stFileUploader > div > div::after {
                    content: "Drag and drop files here or click to browse";
                    font-size: 1.2em;
                    color: #666;
                    margin-top: 10px;
                }
            </style>
        """,
            unsafe_allow_html=True,
        )

        # Add some vertical spacing before the uploader
        st.markdown("<br>", unsafe_allow_html=True)

        # Use Streamlit's native file uploader
        uploaded_files = st.file_uploader(
            " ",  # Empty label since we're using custom text in CSS
            accept_multiple_files=True,
            type=["mkv", "mp4", "avi", "mov", "wmv"],
            label_visibility="collapsed",
        )

        # Add some vertical spacing after the uploader
        st.markdown("<br>", unsafe_allow_html=True)

        if uploaded_files:
            self.handle_uploaded_files(uploaded_files)

    def handle_uploaded_files(self, files):
        """Handle uploaded files and store their paths."""
        if not files:
            return

        # Clear existing files to prevent duplicates
        st.session_state.files = []

        for file in files:
            try:
                # Store file info
                file_info = {
                    "name": file.name,
                    "size": getattr(file, "size", None),
                    "urls": getattr(file, "_file_urls", None),
                    "status": "Ready",  # Initial status
                }
                st.session_state.files.append(file_info)

            except Exception as e:
                st.error(f"Error handling file {file.name}: {str(e)}")

    def rename_files(self):
        """Rename the files with their new names."""
        success_count = 0
        failed_count = 0

        with st.spinner("Renaming files..."):
            for old_name, new_name in st.session_state.renamed_files.items():
                file_info = next(
                    (f for f in st.session_state.files if f["name"] == old_name), None
                )
                if file_info:
                    file_info["status"] = "Processing..."

                try:
                    downloads_dir = os.path.expanduser("~/Downloads")
                    possible_paths = [
                        os.path.join(downloads_dir, folder_name, old_name)
                        for folder_name in os.listdir(downloads_dir)
                        if os.path.isdir(os.path.join(downloads_dir, folder_name))
                    ]

                    actual_path = next(
                        (path for path in possible_paths if os.path.exists(path)), None
                    )

                    if not actual_path:
                        raise FileNotFoundError("File not found")

                    new_path = os.path.join(os.path.dirname(actual_path), new_name)

                    if os.path.exists(new_path):
                        raise FileExistsError("Destination exists")

                    os.rename(actual_path, new_path)
                    file_info["status"] = "Success"
                    success_count += 1

                except Exception as e:
                    if file_info:
                        file_info["status"] = f"Failed - {str(e)}"
                    failed_count += 1

        if success_count > 0:
            st.success(f"✓ Successfully renamed {success_count} file(s)")
        if failed_count > 0:
            st.error(f"⚠ Failed to rename {failed_count} file(s)")

        if failed_count == 0 and success_count > 0:
            st.session_state.renamed_files.clear()
            st.session_state.files.clear()

            upload_dir = os.path.join(os.getcwd(), "uploads")
            if os.path.exists(upload_dir):
                shutil.rmtree(upload_dir)

    def display_file_list(self):
        """Display the list of files to be renamed."""
        if not st.session_state.files:
            return

        # Create DataFrame
        data = []
        for file in st.session_state.files:
            new_name = st.session_state.renamed_files.get(file["name"], "")
            # Update status based on successful rename
            downloads_dir = os.path.expanduser("~/Downloads")
            folder_path = next(
                (
                    folder
                    for folder in Path(downloads_dir).iterdir()
                    if folder.is_dir()
                    and new_name in (f.name for f in folder.iterdir())
                ),
                None,
            )

            if new_name and folder_path:
                file["status"] = "Success"
            status = file["status"]
            data.append(
                {"Original Name": file["name"], "New Name": new_name, "Status": status}
            )

        df = pd.DataFrame(data)

        # Display the DataFrame with text wrapping
        status_colors = {
            "Success": "#4caf50",
            "Processing...": "#2196f3",
            "Ready": "#ff9800",
        }

        def apply_status_color(v):
            if v.startswith("Failed"):
                return "color: #f44336"
            return f"color: {status_colors.get(v, '')}"

        st.dataframe(
            df.style.applymap(apply_status_color, subset=["Status"]).set_properties(
                **{
                    "text-align": "left",
                    "white-space": "pre-wrap",
                    "max-width": "400px",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    def undo_renames(self):
        """Undo the rename operations."""
        success_count, failed_count = 0, 0

        with st.spinner("Undoing renames..."):
            for old_name, new_name in st.session_state.renamed_files.items():
                # Find file info for the current file
                file_info = next(
                    (f for f in st.session_state.files if f["name"] == old_name), None
                )
                if file_info:
                    file_info["status"] = "Processing..."

                try:
                    # Determine folder path in Downloads
                    downloads_dir = Path.home() / "Downloads"
                    folder_path = next(
                        (
                            folder
                            for folder in downloads_dir.iterdir()
                            if folder.is_dir()
                            and any(
                                folder.joinpath(f).name == old_name
                                for f in folder.iterdir()
                            )
                        ),
                        None,
                    )

                    # Construct paths for old and new filenames
                    new_path, old_path = os.path.join(
                        folder_path, new_name
                    ), os.path.join(folder_path, old_name)

                    # Check if renamed file exists
                    if not os.path.exists(new_path):
                        self._update_status(
                            file_info, "Failed - Renamed file not found"
                        )
                        failed_count += 1
                        continue

                    # Check if original file already exists
                    if os.path.exists(old_path):
                        self._update_status(
                            file_info, "Failed - Original name already exists"
                        )
                        failed_count += 1
                        continue

                    # Rename file back to original
                    os.rename(new_path, old_path)
                    self._update_status(file_info, "Ready")
                    success_count += 1

                except Exception as e:
                    self._update_status(file_info, f"Failed - {str(e)}")
                    failed_count += 1

        # Display summary of undo operations
        self._display_undo_summary(success_count, failed_count)

    def _update_status(self, file_info, status):
        """Update the status of a file."""
        if file_info:
            file_info["status"] = status

    def _display_undo_summary(self, success_count, failed_count):
        """Display a summary of the undo operations."""
        if success_count > 0:
            st.success(f"✓ Successfully undid {success_count} rename(s)")
        if failed_count > 0:
            st.error(f"⚠ Failed to undo {failed_count} rename(s)")
        if failed_count == 0:
            # Clear renamed files if all undos were successful
            st.session_state.renamed_files.clear()

    def display_action_buttons(self):
        """Display action buttons."""
        if not st.session_state.renamed_files:
            return

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Start Batch", use_container_width=True):
                self.rename_files()

        with col2:
            if st.button("Undo Batch", use_container_width=True):
                self.undo_renames()

    def run(self):
        """Run the Streamlit application."""
        st.title("TV Show Renamer")

        # Main layout
        self.display_drop_zone()
        self.select_tv_show()
        self.display_file_list()
        self.display_action_buttons()

# Run the app
def main():
    app = StreamlitTVShowRenamer()
    app.run()


if __name__ == "__main__":
    main()
