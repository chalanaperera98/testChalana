"""GetCoords
Gets coordinates of foundations and columns."""

__title__ = "GetCoords"
__author__ = "Chalana"

import os

from pyrevit import revit, DB, UI, script, forms
from pyrevit.forms import WPFWindow
import traceback
import clr
import System
clr.AddReference("System.Windows.Presentation")
clr.AddReference("System.Drawing")
from System.Windows.Media.Imaging import BitmapImage
from System.Windows.Media import Brushes, Color, SolidColorBrush
from System import Uri

doc = revit.doc
app = doc.Application

def get_survey_point():
    return DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_SharedBasePoint).WhereElementIsNotElementType().FirstElement()

def get_project_base_point():
    return DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_ProjectBasePoint).WhereElementIsNotElementType().FirstElement()

class CoordinateOptionsForm(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)
        
        # Mapping elements explicitly just in case
        self.foundation_list = self.FindName("FoundationList")
        self.column_list = self.FindName("ColumnList")
        self.coord_combo = self.FindName("CoordSystemCombo")
        self.units_combo = self.FindName("UnitsCombo")
        # Bind the Update button
        try:
            self.UpdateBtn = self.window.FindName("UpdateBtn")
            self.UpdateBtn.Click += self.UpdateBtn_Click
        except:
            pass
            
        self.logo_img = self.window.FindName("LogoImage")

        # Determine available Family Types in the model
        foundation_instances = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_StructuralFoundation).WhereElementIsNotElementType().ToElements()
        column_instances = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_StructuralColumns).WhereElementIsNotElementType().ToElements()
        
        foundation_names = []
        for f in foundation_instances:
            f_type = revit.doc.GetElement(f.GetTypeId())
            if f_type:
                fam_name = f_type.FamilyName if hasattr(f_type, 'FamilyName') else f_type.Family.Name
                type_name = f_type.Name if hasattr(f_type, 'Name') else f_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
                foundation_names.append(fam_name + " - " + type_name)
        foundation_names = sorted(list(set(foundation_names)))
        
        column_names = []
        for c in column_instances:
            c_type = revit.doc.GetElement(c.GetTypeId())
            if c_type:
                fam_name = c_type.FamilyName if hasattr(c_type, 'FamilyName') else c_type.Family.Name
                type_name = c_type.Name if hasattr(c_type, 'Name') else c_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
                column_names.append(fam_name + " - " + type_name)
        column_names = sorted(list(set(column_names)))
        
        # Populate ListBoxes
        self.foundation_list.ItemsSource = foundation_names
        self.column_list.ItemsSource = column_names
        
        # Force Colors Programmatically (In case XAML styles fail)
        pure_black = Brushes.Black
        white_brush = Brushes.White
        red_accent = SolidColorBrush(Color.FromRgb(128, 47, 45)) # RGB 128, 47, 45
        
        # Window Background
        self.Background = pure_black
        
        self.foundation_list.Background = pure_black
        self.foundation_list.Foreground = white_brush
        self.column_list.Background = pure_black
        self.column_list.Foreground = white_brush
        
        self.coord_combo.Background = pure_black
        self.coord_combo.Foreground = white_brush
        self.units_combo.Background = pure_black
        self.units_combo.Foreground = white_brush
        
        # Default selections
        self.coord_combo.SelectedIndex = 0
        self.units_combo.SelectedIndex = 0

        self.load_logo()
        
    def UpdateBtn_Click(self, sender, e):
        """Handle the manual update button click."""
        import subprocess
        git_exe = r"C:\Program Files\Git\bin\git.exe"
        # Determine repo directory
        repo_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        if "test_chalana.extension" in repo_dir and "testChalana" not in repo_dir:
            repo_dir = os.path.join(repo_dir, "testChalana")

        if not os.path.exists(git_exe):
            show_custom_alert("Git executable not found at: {}".format(git_exe))
            return

        try:
            forms.toast("Checking for updates...", title="Get Coordinates")
            
            # Fetch updates from origin
            subprocess.call([git_exe, "-C", repo_dir, "fetch", "origin", "main"])
            
            # Check if we are behind
            process = subprocess.Popen(
                [git_exe, "-C", repo_dir, "status"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = process.communicate()
            
            if "behind" in stdout:
                # Show custom update popup
                xaml_file = os.path.join(os.path.dirname(__file__), "update_popup.xaml")
                if os.path.exists(xaml_file):
                    popup = UpdatePopupWindow(xaml_file)
                    if popup.ShowDialog():
                        # Pull latest changes
                        pull_process = subprocess.Popen(
                            [git_exe, "-C", repo_dir, "pull", "origin", "main"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        pull_out, pull_err = pull_process.communicate()
                        
                        if pull_process.returncode == 0:
                            show_custom_alert("Successfully updated to the latest version!\n\nPlease restart the tool or reload pyRevit to apply changes.")
                        else:
                            show_custom_alert("Update failed:\n{}".format(pull_err))
                else:
                    # Fallback to standard alert if xaml missing
                    res = forms.alert("A new update is available on GitHub. Would you like to update now?", 
                                    title="Update Found", 
                                    ok=True, cancel=True)
                    if res:
                        subprocess.call([git_exe, "-C", repo_dir, "pull", "origin", "main"])
                        show_custom_alert("Successfully updated to the latest version!")
            else:
                forms.toast("You are already using the latest version.", title="Up-to-Date")
                
        except Exception as ex:
            show_custom_alert("Error during update: {}".format(str(ex)))
        
    def RunButton_Click(self, sender, args):
        self.selected_foundations = list(self.foundation_list.SelectedItems)
        self.selected_columns = list(self.column_list.SelectedItems)
        
        self.is_survey_point = (self.coord_combo.SelectedIndex == 0)
        self.is_meters = (self.units_combo.SelectedIndex == 0)
        
        if not self.selected_foundations and not self.selected_columns:
            forms.alert("Please select at least one Foundation or Column type.")
            return
            
        self.DialogResult = True
        self.Close()

    def load_logo(self):
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
            if os.path.exists(logo_path):
                uri = Uri(logo_path)
                bitmap = BitmapImage(uri)
                if self.logo_img:
                    self.logo_img.Source = bitmap
        except Exception as e:
            print("Logo loading error: {}".format(e))

    def TitleBar_MouseDown(self, sender, args):
        if args.LeftButton == System.Windows.Input.MouseButtonState.Pressed:
            self.DragMove()

    def CancelButton_Click(self, sender, args):
        self.DialogResult = False
        self.Close()

    def SelectAllFounds_Click(self, sender, args):
        self.foundation_list.SelectAll()
        
    def ClearFounds_Click(self, sender, args):
        self.foundation_list.UnselectAll()
        
    def SelectAllCols_Click(self, sender, args):
        self.column_list.SelectAll()
        
    def ClearCols_Click(self, sender, args):
        self.column_list.UnselectAll()

class AlertWindow(WPFWindow):
    def __init__(self, xaml_file_name, message):
        WPFWindow.__init__(self, xaml_file_name)
        self.MessageText.Text = message

    def TitleBar_MouseDown(self, sender, args):
        if args.LeftButton == System.Windows.Input.MouseButtonState.Pressed:
            self.DragMove()

    def OKButton_Click(self, sender, args):
        self.DialogResult = True
        self.Close()

def show_custom_alert(message):
    try:
        xaml_file = os.path.join(os.path.dirname(__file__), "alert.xaml")
        if os.path.exists(xaml_file):
            alert = AlertWindow(xaml_file, message)
            alert.ShowDialog()
        else:
            forms.alert(message)
    except:
        forms.alert(message)

class UpdatePopupWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

    def TitleBar_MouseDown(self, sender, args):
        if args.LeftButton == System.Windows.Input.MouseButtonState.Pressed:
            self.DragMove()

    def UpdateNow_Click(self, sender, args):
        self.DialogResult = True
        self.Close()

    def CancelButton_Click(self, sender, args):
        self.DialogResult = False
        self.Close()

def process_elements(selected_founds, selected_cols, is_survey_point, is_meters):
    t = DB.Transaction(doc, "Add Coordinates to Identity Data")
    t.Start()
    
    try:
        # Setup Shared Parameters File
        sp_file = app.SharedParametersFilename
        if not sp_file or not os.path.exists(sp_file):
            temp_sp = os.path.join(os.path.expanduser('~'), "Documents", "Revit_SharedParams.txt")
            if not os.path.exists(temp_sp):
                with open(temp_sp, 'w') as f:
                    f.write("# This is a Revit shared parameter file.\n*META\tVERSION\tMINVERSION\nMETA\t2\t1\n*GROUP\tID\tNAME\n*PARAM\tGUID\tNAME\tDATATYPE\tDATACATEGORY\tGROUP\tVISIBLE\tDESCRIPTION\tUSERMODIFIABLE\tHIDEWHENNOVALUE\n")
            app.SharedParametersFilename = temp_sp
            
        sp_file_def = app.OpenSharedParameterFile()
        if not sp_file_def:
            show_custom_alert("Could not access Shared Parameters file.")
            return
            
        # Setup Parameter Group
        group_name = "Coordinates Group"
        group = sp_file_def.Groups.get_Item(group_name)
        if not group:
            group = sp_file_def.Groups.Create(group_name)
            
        param_names = ["Coord_X", "Coord_Y", "Coord_Z"]
        param_defs = []
        
        for p_name in param_names:
            p_def = group.Definitions.get_Item(p_name)
            if not p_def:
                try:
                    # Revit 2022+ API
                    opt = DB.ExternalDefinitionCreationOptions(p_name, DB.SpecTypeId.String.Text)
                except AttributeError:
                    # Pre-Revit 2022 API
                    opt = DB.ExternalDefinitionCreationOptions(p_name, DB.ParameterType.Text)
                p_def = group.Definitions.Create(opt)
            param_defs.append(p_def)
            
        # Bind Parameters
        cat_foundation = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_StructuralFoundation)
        cat_column = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_StructuralColumns)
        
        category_set = app.Create.NewCategorySet()
        if selected_founds: category_set.Insert(cat_foundation)
        if selected_cols: category_set.Insert(cat_column)
        
        bm = doc.ParameterBindings
        try: target_group = DB.GroupTypeId.IdentityData
        except AttributeError: target_group = DB.BuiltInParameterGroup.PG_IDENTITY_DATA
        
        for p_def in param_defs:
            binding = bm.get_Item(p_def)
            if not binding:
                new_binding = app.Create.NewInstanceBinding(category_set)
                try: bm.Insert(p_def, new_binding, target_group)
                except: bm.Insert(p_def, new_binding, DB.BuiltInParameterGroup.PG_IDENTITY_DATA)
            else:
                bound_categories = binding.Categories
                needs_rebind = False
                if selected_founds and not bound_categories.Contains(cat_foundation):
                    bound_categories.Insert(cat_foundation)
                    needs_rebind = True
                if selected_cols and not bound_categories.Contains(cat_column):
                    bound_categories.Insert(cat_column)
                    needs_rebind = True
                if needs_rebind:
                    binding.Categories = bound_categories
                    try: bm.ReInsert(p_def, binding, target_group)
                    except: bm.ReInsert(p_def, binding, DB.BuiltInParameterGroup.PG_IDENTITY_DATA)
                    
        # Collect Elements
        all_elements = []
        if selected_founds:
            founds = DB.FilteredElementCollector(doc).WhereElementIsNotElementType().OfCategory(DB.BuiltInCategory.OST_StructuralFoundation).ToElements()
            for f in founds:
                f_type = doc.GetElement(f.GetTypeId())
                if f_type:
                    fam_name = f_type.FamilyName if hasattr(f_type, 'FamilyName') else f_type.Family.Name
                    type_name = f_type.Name if hasattr(f_type, 'Name') else f_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
                    if (fam_name + " - " + type_name) in selected_founds:
                        all_elements.append(f)
                    
        if selected_cols:
            cols = DB.FilteredElementCollector(doc).WhereElementIsNotElementType().OfCategory(DB.BuiltInCategory.OST_StructuralColumns).ToElements()
            for c in cols:
                c_type = doc.GetElement(c.GetTypeId())
                if c_type:
                    fam_name = c_type.FamilyName if hasattr(c_type, 'FamilyName') else c_type.Family.Name
                    type_name = c_type.Name if hasattr(c_type, 'Name') else c_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
                    if (fam_name + " - " + type_name) in selected_cols:
                        all_elements.append(c)

        # Regenerate to ensure parameter bindings are accessible
        doc.Regenerate()

        # Coordinate System Transform logic
        # Revit API gives points relative to the Internal Origin.
        
        active_project_location = doc.ActiveProjectLocation
        project_position = active_project_location.GetProjectPosition(DB.XYZ.Zero)
        
        # PBP coordinates relative to internal:
        pbp = get_project_base_point()
        sp = get_survey_point()
        
        # Unit multipliers to convert from Decimal Feet
        unit_mult = 0.3048 if is_meters else 304.8
        
        count = 0
        skipped_no_pt = 0
        skipped_no_param = 0
        
        for el in all_elements:
            pt = None
            loc = el.Location
            if loc and isinstance(loc, DB.LocationPoint):
                pt = loc.Point
            elif loc and isinstance(loc, DB.LocationCurve):
                pt = loc.Curve.Evaluate(0.5, True)
                
            if not pt:
                # Fallback to bounding box center if no location point/curve exist
                bbox = el.get_BoundingBox(None)
                if bbox:
                    pt = (bbox.Min + bbox.Max) / 2.0
                
            if pt:
                # Convert Internal point to Survey Point or Project Base Point
                pp = doc.ActiveProjectLocation.GetProjectPosition(pt)
                
                sp_x = pp.EastWest
                sp_y = pp.NorthSouth
                sp_z = pp.Elevation
                
                if not is_survey_point:
                    sp_x -= project_position.EastWest
                    sp_y -= project_position.NorthSouth
                    sp_z -= project_position.Elevation
                
                final_x = sp_x * unit_mult
                final_y = sp_y * unit_mult
                final_z = sp_z * unit_mult
                
                def set_param(element, p_name, p_val, str_val):
                    p_list = element.GetParameters(p_name)
                    for p in p_list:
                        if not p.IsReadOnly:
                            try:
                                if p.StorageType == DB.StorageType.String:
                                    p.Set(str_val)
                                    return True
                                else:
                                    p.Set(p_val)
                                    return True
                            except:
                                pass
                    return False
                
                sx = "{:.3f}".format(final_x)
                sy = "{:.3f}".format(final_y)
                sz = "{:.3f}".format(final_z)
                
                success_x = set_param(el, "Coord_X", final_x, sx)
                success_y = set_param(el, "Coord_Y", final_y, sy)
                success_z = set_param(el, "Coord_Z", final_z, sz)
                
                if success_x and success_y and success_z:
                    count += 1
                else:
                    skipped_no_param += 1
            else:
                skipped_no_pt += 1
                
        t.Commit()
        
        msg = "Successfully retrieved coordinates for {} elements.".format(count)
        if skipped_no_pt > 0:
            msg += "\nSkipped {} elements with no geometry/location.".format(skipped_no_pt)
        if skipped_no_param > 0:
            msg += "\nSkipped {} elements because params were read-only or not found.".format(skipped_no_param)
            
        show_custom_alert(msg)
        
    except Exception as e:
        if t.HasStarted() and not t.HasEnded():
            t.RollBack()
        traceback.print_exc()
        show_custom_alert("Error occurred:\n{}".format(str(e)))

def main():
    if doc.IsFamilyDocument:
        show_custom_alert("This tool must be run in a Project document.")
        return

    script_dir = os.path.dirname(__file__)
    xaml_file = os.path.join(script_dir, "ui.xaml")
    
    form = CoordinateOptionsForm(xaml_file)
    if form.ShowDialog():
        process_elements(form.selected_foundations, form.selected_columns, form.is_survey_point, form.is_meters)

if __name__ == '__main__':
    main()
