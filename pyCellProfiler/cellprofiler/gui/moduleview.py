"""ModuleView.py - implements a view on a module

CellProfiler is distributed under the GNU General Public License.
See the accompanying file LICENSE for details.

Developed by the Broad Institute
Copyright 2003-2009

Please see the AUTHORS file for credits.

Website: http://www.cellprofiler.org
"""
__version__="$Revision$"
import wx
import wx.grid
import cellprofiler.pipeline
import cellprofiler.settings
from regexp_editor import edit_regexp

ERROR_COLOR = wx.RED
RANGE_TEXT_WIDTH = 40 # number of pixels in a range text box TO_DO - calculate it
ABSOLUTE = "Absolute"
FROM_EDGE = "From edge"

class SettingEditedEvent:
    """Represents an attempt by the user to edit a setting
    
    """
    def __init__(self,setting,proposed_value,event):
        self.__setting = setting
        self.__proposed_value = proposed_value
        self.__event = event
        self.__accept_change = True
    
    def get_setting(self):
        """Return the setting being edited
        
        """
        return self.__setting
    
    def get_proposed_value(self):
        """Return the value proposed by the user
        
        """
        return self.__proposed_value
    
    def cancel(self):
        self.__accept_change = False
        
    def accept_change(self):
        return self.__accept_change
    def ui_event(self):
        """The event from the UI that triggered the edit
        
        """
        return self.__event

def text_control_name(v):
    """Return the name of a setting's text control
    v - the setting
    The text control name is built using the setting's key
    """
    return "%s_text"%(str(v.key()))

def button_control_name(v):
    """Return the name of a setting's button
    v - the setting
    """
    return "%s_button"%(str(v.key()))

def edit_control_name(v):
    """Return the name of a setting's edit control
    v - the setting
    The edit control name is built using the setting's key
    """
    return str(v.key())

def min_control_name(v):
    """For a range, return the control that sets the minimum value
    v - the setting
    """
    return "%s_min"%(str(v.key()))

def max_control_name(v):
    """For a range, return the control that sets the maximum value
    v - the setting
    """
    return "%s_max"%(str(v.key()))

def absrel_control_name(v):
    """For a range, return the control that chooses between absolute and relative
    
    v - the setting
    Absolute - far coordinate is an absolute value
    From edge - far coordinate is a distance from the far edge
    """
    return "%s_absrel"%(str(v.key()))

def x_control_name(v):
    """For coordinates, return the control that sets the x value
    v - the setting
    """
    return "%s_x"%(str(v.key()))

def y_control_name(v):
    """For coordinates, return the control that sets the y value
    v - the setting
    """
    return "%s_y"%(str(v.key()))

def category_control_name(v):
    '''For measurements, return the control that sets the measurement category
    
    v - the setting
    '''
    return "%s_category"%(str(v.key()))

def category_text_control_name(v):
    return "%s_category_text"%(str(v.key()))

def feature_control_name(v):
    '''For measurements, return the control that sets the feature name

    v - the setting
    '''
    return "%s_feature"%(str(v.key()))

def feature_text_control_name(v):
    return "%s_feature_text"%(str(v.key()))

def image_control_name(v):
    '''For measurements, return the control that sets the image name

    v - the setting
    '''
    return "%s_image"%(str(v.key()))

def image_text_control_name(v):
    return "%s_image_text"%(str(v.key()))

def scale_control_name(v):
    '''For measurements, return the control that sets the measurement scale

    v - the setting
    '''
    return "%s_scale"%(str(v.key()))

def scale_text_ctrl_name(v):
    return "%s_scale_text"%(str(v.key()))

def encode_label(text):
    """Encode text escapes for the static control and button labels
    
    The ampersand (&) needs to be encoded as && for wx.StaticText
    and wx.Button in order to keep it from signifying an accelerator.
    """
    return text.replace('&','&&')
  
class ModuleView:
    """The module view implements a view on CellProfiler.Module
    
    The module view implements a view on CellProfiler.Module. The view consists
    of a table composed of one row per setting. The first column of the table
    has the explanatory text and the second has a control which
    gives the ui for editing the setting.
    """
    
    def __init__(self,module_panel,pipeline):
        self.__module_panel = module_panel
        self.__pipeline = pipeline
        pipeline.add_listener(self.__on_pipeline_event)
        self.__listeners = []
        self.__value_listeners = []
        self.__module = None
        self.__sizer = None
        self.__module_panel.SetVirtualSizeWH(0,0)
        self.__module_panel.SetupScrolling()
        wx.EVT_IDLE(module_panel,self.on_idle)

    def __set_columns(self):
        self.__grid.SetColLabelValue(0,'Setting description')
        self.__grid.SetColLabelValue(1,'Value')
        self.__grid.SetColSize(1,70)
    
    def get_module_panel(self):
        """The panel that hosts the module controls
        
        This is exposed for testing purposes.
        """
        return self.__module_panel
    
    module_panel = property(get_module_panel)
    
    def clear_selection(self):
        if self.__module:
            for listener in self.__value_listeners:
                listener['notifier'].remove_listener(listener['listener'])
            self.__value_listeners = []
            self.__module = None
            self.__sizer.Reset(0,2)
    
    def hide_settings(self):
        for child in self.__module_panel.Children:
            child.Hide()
        
    def set_selection(self,module_num):
        """Initialize the controls in the view to the settings of the module"""
        self.module_panel.Freeze()
        try:
            reselecting         = (self.__module and
                                   self.__module.module_num == module_num)
            if not reselecting:
                self.clear_selection()
            self.__module       = self.__pipeline.module(module_num)
            self.__controls     = []
            self.__static_texts = []
            data                = []
            settings            = self.__module.visible_settings()
            if self.__sizer is None:
                self.__sizer = ModuleSizer(len(settings), 2)
                self.module_panel.SetSizer(self.__sizer)
            else:
                self.__sizer.Reset(len(settings), 2, False)
            sizer    = self.__sizer
            if reselecting:
                self.hide_settings()
            
            for v,i in zip(settings, range(0,len(settings))):
                control_name = edit_control_name(v)
                text_name    = text_control_name(v)
                static_text  = self.__module_panel.FindWindowByName(text_name)
                control      = self.__module_panel.FindWindowByName(control_name)
                if static_text:
                    static_text.Show()
                    static_text.Label = encode_label(v.text)
                else:
                    static_text = wx.StaticText(self.__module_panel,
                                                -1,
                                                encode_label(v.text),
                                                style=wx.ALIGN_RIGHT,
                                                name=text_name)
                sizer.Add(static_text,3,wx.EXPAND|wx.ALL,2)
                if control:
                    control.Show()
                self.__static_texts.append(static_text)
                if isinstance(v,cellprofiler.settings.Binary):
                    control = self.make_binary_control(v,control_name,control)
                elif isinstance(v,cellprofiler.settings.Choice):
                    control = self.make_choice_control(v, v.get_choices(),
                                                       control_name, 
                                                       wx.CB_READONLY,
                                                       control)
                elif isinstance(v,cellprofiler.settings.CustomChoice):
                    control = self.make_choice_control(v, v.get_choices(),
                                                       control_name, 
                                                       wx.CB_DROPDOWN,
                                                       control)
                elif isinstance(v,cellprofiler.settings.NameSubscriber):
                    choices = v.get_choices(self.__pipeline)
                    control = self.make_choice_control(v, choices,
                                                       control_name, 
                                                       wx.CB_DROPDOWN,
                                                       control)
                elif isinstance(v,cellprofiler.settings.FigureSubscriber):
                    choices = v.get_choices(self.__pipeline)
                    control = self.make_choice_control(v, choices,
                                                       control_name, 
                                                       wx.CB_DROPDOWN,
                                                       control)
                elif isinstance(v, cellprofiler.settings.DoSomething):
                    control = self.make_callback_control(v, control_name,
                                                         control)
                elif isinstance(v, cellprofiler.settings.IntegerRange) or\
                     isinstance(v, cellprofiler.settings.FloatRange):
                    control = self.make_range_control(v, control)
                elif isinstance(v, cellprofiler.settings.IntegerOrUnboundedRange):
                    control = self.make_unbounded_range_control(v, control)
                elif isinstance(v, cellprofiler.settings.Coordinates):
                    control = self.make_coordinates_control(v,control)
                elif isinstance(v, cellprofiler.settings.RegexpText):
                    control = self.make_regexp_control(v, control)
                elif isinstance(v, cellprofiler.settings.Measurement):
                    control = self.make_measurement_control(v, control)
                else:
                    control = self.make_text_control(v, control_name, control)
                sizer.Add(control,1,wx.EXPAND|wx.ALL,2)
                self.__controls.append(control)
            self.__module_panel.Layout()
        finally:
            self.module_panel.Thaw()
            self.module_panel.Refresh()
    
    def make_binary_control(self,v,control_name, control):
        """Make a checkbox control for a Binary setting"""
        if not control:
            control = wx.CheckBox(self.__module_panel,-1,name=control_name)
            def callback(event, setting=v, control=control):
                self.__on_checkbox_change(event, setting, control)
                
            self.__module_panel.Bind(wx.EVT_CHECKBOX,
                                     callback,
                                     control)
        control.SetValue(v.is_yes)
        return control
    
    def make_choice_control(self,v,choices,control_name,style,control):
        """Make a combo-box that shows choices
        
        v            - the setting
        choices      - the possible values for the setting
        control_name - assign this name to the control
        style        - one of the CB_ styles 
        """
        if not control:
            control = wx.ComboBox(self.__module_panel,-1,v.value,
                                  choices=choices,
                                  style=style,
                                  name=control_name)
            def callback(event, setting=v, control = control):
                self.__on_combobox_change(event, setting,control)
            self.__module_panel.Bind(wx.EVT_COMBOBOX,callback,control)
            if style == wx.CB_DROPDOWN:
                def on_cell_change(event, setting=v, control=control):
                     self.__on_cell_change(event, setting, control)
                self.__module_panel.Bind(wx.EVT_TEXT,on_cell_change,control)
        else:
            old_choices = control.Items
            if len(choices)!=len(old_choices) or\
               not all([x==y for x,y in zip(choices,old_choices)]):
                control.Items = choices
            if control.Value != v.value:
                control.Value = v.value
            
        return control
    
    def make_callback_control(self,v,control_name,control):
        """Make a control that calls back using the callback buried in the setting"""
        if not control:
            control = wx.Button(self.module_panel,-1,
                                v.label,name=control_name)
            def callback(event, setting=v):
                self.__on_do_something(event, setting)
                
            self.module_panel.Bind(wx.EVT_BUTTON, callback, control)
        return control
    
    def make_regexp_control(self, v, control):
        """Make a textbox control + regular expression button"""
        if not control:
            panel = wx.Panel(self.__module_panel,
                             -1,
                             name=edit_control_name(v))
            control = panel
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            panel.SetSizer(sizer)
            text_ctrl = wx.TextCtrl(panel, -1, str(v.value),
                                    name=text_control_name(v))
            sizer.Add(text_ctrl,1,wx.EXPAND|wx.RIGHT,1)
            bitmap = wx.ArtProvider.GetBitmap(wx.ART_FIND,wx.ART_TOOLBAR,(16,16))
            bitmap_button = wx.BitmapButton(panel, bitmap=bitmap,
                                            name=button_control_name(v))
            sizer.Add(bitmap_button,0,wx.EXPAND)
            def on_cell_change(event, setting = v, control=text_ctrl):
                self.__on_cell_change(event, setting,control)
                
            def on_button_pressed(event, setting = v, control = text_ctrl):
                new_value = edit_regexp(panel, control.Value, 
                                        "plateA-2008-08-06_A12_s1_w1_[89A882DE-E675-4C12-9F8E-46C9976C4ABE].tif")
                if new_value:
                    control.Value = new_value
                    self.__on_cell_change(event, setting,control)
                
            self.__module_panel.Bind(wx.EVT_TEXT, on_cell_change, text_ctrl)
            self.__module_panel.Bind(wx.EVT_BUTTON, on_button_pressed, bitmap_button)
        else:
            text_control = control.FindWindowByName(text_control_name(v))
            text_control.Value = v.value
        return control
     
    def make_text_control(self, v, control_name, control):
        """Make a textbox control"""
        if not control:
            control = wx.TextCtrl(self.__module_panel,
                                  -1,
                                  str(v),
                                  name=control_name)
            def on_cell_change(event, setting = v, control=control):
                self.__on_cell_change(event, setting,control)
            self.__module_panel.Bind(wx.EVT_TEXT,on_cell_change,control)
        elif control.Value != v.value:
            control.Value = str(v.value)
        return control
    
    def make_range_control(self, v, panel):
        """Make a "control" composed of a panel and two edit boxes representing a range"""
        if not panel:
            panel = wx.Panel(self.__module_panel,-1,name=edit_control_name(v))
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            panel.SetSizer(sizer)
            min_ctrl = wx.TextCtrl(panel,-1,str(v.min),
                                   name=min_control_name(v))
            best_width = min_ctrl.GetCharWidth()*5
            min_ctrl.SetInitialSize(wx.Size(best_width,-1))
            sizer.Add(min_ctrl,0,wx.EXPAND|wx.RIGHT,1)
            max_ctrl = wx.TextCtrl(panel,-1,str(v.max),
                                   name=max_control_name(v))
            max_ctrl.SetInitialSize(wx.Size(best_width,-1))
            sizer.Add(max_ctrl,0,wx.EXPAND)
            def on_min_change(event, setting = v, control=min_ctrl):
                self.__on_min_change(event, setting,control)
            self.__module_panel.Bind(wx.EVT_TEXT,on_min_change,min_ctrl)
            def on_max_change(event, setting = v, control=max_ctrl):
                self.__on_max_change(event, setting,control)
            self.__module_panel.Bind(wx.EVT_TEXT,on_max_change,max_ctrl)
        else:
            min_ctrl = panel.FindWindowByName(min_control_name(v))
            if min_ctrl.Value != str(v.min):
                min_ctrl.Value = str(v.min)
            max_ctrl = panel.FindWindowByName(max_control_name(v))
            if max_ctrl.Value != str(v.max):
                min_ctrl.Value = str(v.max)
            
        return panel
    
    def make_unbounded_range_control(self, v, panel):
        """Make a "control" composed of a panel and two combo-boxes representing a range
        
        v - an IntegerOrUnboundedRange setting
        panel - put it in this panel
        
        The combo box has the word to use to indicate that the range is unbounded
        and the text portion is the value
        """
        if not panel:
            panel = wx.Panel(self.__module_panel,-1,name=edit_control_name(v))
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            panel.SetSizer(sizer)
            min_ctrl = wx.TextCtrl(panel,-1,value=str(v.min),
                                   name=min_control_name(v))
            best_width = min_ctrl.GetCharWidth()*5
            min_ctrl.SetInitialSize(wx.Size(best_width,-1))
            sizer.Add(min_ctrl,0,wx.EXPAND|wx.RIGHT,1)
            max_ctrl = wx.TextCtrl(panel,-1,value=v.display_max,
                                   name=max_control_name(v))
            max_ctrl.SetInitialSize(wx.Size(best_width,-1))
            sizer.Add(max_ctrl,0,wx.EXPAND)
            if v.unbounded_max or v.max < 0:
                value = FROM_EDGE
            else:
                value = ABSOLUTE 
            absrel_ctrl = wx.ComboBox(panel,-1,value,
                                      choices = [ABSOLUTE,FROM_EDGE],
                                      name = absrel_control_name(v),
                                      style = wx.CB_DROPDOWN|wx.CB_READONLY)
            sizer.Add(absrel_ctrl,0,wx.EXPAND|wx.RIGHT,1)
            def on_min_change(event, setting = v, control=min_ctrl):
                old_value = str(setting)
                if setting.unbounded_max:
                    max_value = cellprofiler.settings.END
                else:
                    max_value = str(setting.max)
                proposed_value="%s,%s"%(str(control.Value),max_value)
                setting_edited_event = SettingEditedEvent(setting,
                                                          proposed_value,event)
                self.notify(setting_edited_event)
                
            self.__module_panel.Bind(wx.EVT_TEXT,on_min_change,min_ctrl)
            def on_max_change(event, setting = v, control=max_ctrl, 
                              absrel_ctrl=absrel_ctrl):
                old_value = str(setting)
                if (absrel_ctrl.Value == ABSOLUTE):
                    max_value = str(control.Value)
                elif control.Value == '0':
                    max_value = cellprofiler.settings.END
                else:
                    max_value = "-"+str(control.Value)
                proposed_value="%s,%s"%(setting.display_min,max_value)
                setting_edited_event = SettingEditedEvent(setting,
                                                          proposed_value,event)
                self.notify(setting_edited_event)
            self.__module_panel.Bind(wx.EVT_TEXT,on_max_change,max_ctrl)
            def on_absrel_change(event, setting = v, control=absrel_ctrl):
                if not v.unbounded_max:
                    old_value = str(setting)
                    
                    if control.Value == ABSOLUTE:
                        proposed_value="%s,%s"%(setting.display_min,
                                                setting.max)
                    else:
                        proposed_value="%s,%d"%(setting.display_min,
                                                -abs(setting.max))
                else:
                    proposed_value="%s,%s"%(setting.display_min,
                                            cellprofiler.settings.END)
                setting_edited_event = SettingEditedEvent(setting,
                                                          proposed_value,event)
                self.notify(setting_edited_event)
            self.__module_panel.Bind(wx.EVT_COMBOBOX,
                                     on_absrel_change,absrel_ctrl)
        else:
            min_ctrl = panel.FindWindowByName(min_control_name(v))
            if min_ctrl.Value != v.display_min:
                min_ctrl.Value = v.display_min
            max_ctrl = panel.FindWindowByName(max_control_name(v))
            if max_ctrl.Value != v.display_max:
                min_ctrl.Value = v.display_max
            absrel_ctrl = panel.FindWindowByName(absrel_control_name(v))
            absrel_value = ABSOLUTE
            if v.unbounded_max or v.max < 0:
                absrel_value = FROM_EDGE
            if absrel_ctrl.Value != absrel_value:
                absrel_ctrl.Value = absrel_value
            
        return panel
    
    def make_coordinates_control(self, v, panel):
        """Make a "control" composed of a panel and two edit boxes representing X and Y"""
        if not panel:
            panel = wx.Panel(self.__module_panel,-1,name=edit_control_name(v))
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            panel.SetSizer(sizer)
            sizer.Add(wx.StaticText(panel,-1,"X:"),0,wx.EXPAND|wx.RIGHT,1)
            x_ctrl = wx.TextCtrl(panel,-1,str(v.x),
                                   name=x_control_name(v))
            best_width = x_ctrl.GetCharWidth()*5
            x_ctrl.SetInitialSize(wx.Size(best_width,-1))
            sizer.Add(x_ctrl,0,wx.EXPAND|wx.RIGHT,1)
            sizer.Add(wx.StaticText(panel,-1,"Y:"),0,wx.EXPAND|wx.RIGHT,1)
            y_ctrl = wx.TextCtrl(panel,-1,str(v.y),
                                 name=y_control_name(v))
            y_ctrl.SetInitialSize(wx.Size(best_width,-1))
            sizer.Add(y_ctrl,0,wx.EXPAND)
            def on_x_change(event, setting = v, control=x_ctrl):
                old_value = str(setting)
                proposed_value="%s,%s"%(str(control.Value),str(setting.y))
                setting_edited_event = SettingEditedEvent(setting,
                                                          proposed_value,event)
                self.notify(setting_edited_event)
            self.__module_panel.Bind(wx.EVT_TEXT,on_x_change,x_ctrl)
            def on_y_change(event, setting = v, control=y_ctrl):
                old_value = str(setting)
                proposed_value="%s,%s"%(str(setting.x),str(control.Value))
                setting_edited_event = SettingEditedEvent(setting,
                                                          proposed_value,event)
                self.notify(setting_edited_event)
            self.__module_panel.Bind(wx.EVT_TEXT,on_y_change,y_ctrl)
        else:
            x_ctrl = panel.FindWindowByName(x_control_name(v))
            if x_ctrl.Value != str(v.x):
                x_ctrl.Value = str(v.x)
            y_ctrl = panel.FindWindowByName(y_control_name(v))
            if y_ctrl.Value != str(v.y):
                y_ctrl.Value = str(v.y)
            
        return panel
    
    def make_measurement_control(self, v, panel):
        '''Make a composite measurement control
        
        The measurement control has the following parts:
        Category - a measurement category like AreaShape or Intensity
        Feature name - the feature being measured or algorithm applied
        Image name - an optional image that was used to compute the measurement
        Scale - an optional scale, generally in pixels, that controls the size
                of the measured features.
        '''
        
        if not panel:
            panel = wx.Panel(self.__module_panel,-1,name=edit_control_name(v))
            sizer = wx.BoxSizer(wx.VERTICAL)
            panel.SetSizer(sizer)
            sub_sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(sub_sizer,0,wx.ALIGN_LEFT)
            category_text_ctrl = wx.StaticText(panel,label='Category:',
                                               name = category_text_control_name(v))
            sub_sizer.Add(category_text_ctrl,0, wx.EXPAND|wx.ALL,2)
            category_ctrl = wx.ComboBox(panel, style=wx.CB_READONLY,
                                        name=category_control_name(v))
            sub_sizer.Add(category_ctrl, 0, wx.EXPAND|wx.ALL, 2)
            sub_sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(sub_sizer, 0 , wx.ALIGN_LEFT)
            feature_text_ctrl = wx.StaticText(panel, label='Measurement:',
                                              name= feature_text_control_name(v))
            sub_sizer.Add(feature_text_ctrl, 0, wx.EXPAND | wx.ALL, 2)
            feature_ctrl = wx.ComboBox(panel, style=wx.CB_READONLY,
                                       name=feature_control_name(v))
            sub_sizer.Add(feature_ctrl, 0, wx.EXPAND|wx.ALL, 2)
            sub_sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(sub_sizer, 0, wx.ALIGN_LEFT)
            image_text_ctrl = wx.StaticText(panel, label='Image:',
                                            name = image_text_control_name(v))
            sub_sizer.Add(image_text_ctrl, 0, wx.EXPAND | wx.ALL, 2)
            image_ctrl = wx.ComboBox(panel, style=wx.CB_READONLY,
                                     name=image_control_name(v))
            sub_sizer.Add(image_ctrl, 0, wx.EXPAND|wx.ALL, 2)
            sub_sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(sub_sizer, 0, wx.ALIGN_LEFT)
            scale_text_ctrl = wx.StaticText(panel, label='Scale:',
                                            name = scale_text_ctrl_name(v))
            sub_sizer.Add(scale_text_ctrl, 0, wx.EXPAND | wx.ALL, 2)
            scale_ctrl = wx.ComboBox(panel, style=wx.CB_READONLY,
                                     name=scale_control_name(v))
            sub_sizer.Add(scale_ctrl, 0, wx.EXPAND|wx.ALL, 2)
            max_width = 0
            for sub_sizer_item in sizer.GetChildren():
                static = sub_sizer_item.Sizer.GetChildren()[0].Window
                max_width = max(max_width,static.Size.width)
            for sub_sizer_item in sizer.GetChildren():
                static = sub_sizer_item.Sizer.GetChildren()[0].Window
                static.Size = wx.Size(max_width,static.Size.height)
                static.SetSizeHints(max_width, -1, max_width)
            #
            # Bind all controls to the function that constructs a value
            # out of the parts
            #
            def on_change(event, v=v, category_ctrl = category_ctrl,
                          feature_ctrl = feature_ctrl,
                          image_ctrl = image_ctrl,
                          scale_ctrl = scale_ctrl):
                '''Reconstruct the measurement value if anything changes'''
                def value_of(ctrl):
                    return ctrl.Value if len(ctrl.Strings) else None
                value = v.construct_value(value_of(category_ctrl),
                                          value_of(feature_ctrl),
                                          value_of(image_ctrl),
                                          value_of(scale_ctrl))
                setting_edited_event = SettingEditedEvent(v,value,event)
                self.notify(setting_edited_event)
                self.reset_view()
            
            for ctrl in (category_ctrl, feature_ctrl, image_ctrl, scale_ctrl):
                panel.Bind(wx.EVT_COMBOBOX, on_change, ctrl)
        else:
            category_ctrl = panel.FindWindowByName(category_control_name(v))
            category_text_ctrl = panel.FindWindowByName(category_text_control_name(v))
            feature_ctrl = panel.FindWindowByName(feature_control_name(v))
            feature_text_ctrl = panel.FindWindowByName(feature_text_control_name(v))
            image_ctrl = panel.FindWindowByName(image_control_name(v))
            image_text_ctrl = panel.FindWindowByName(image_text_control_name(v))
            scale_ctrl = panel.FindWindowByName(scale_control_name(v))
            scale_text_ctrl = panel.FindWindowByName(scale_text_ctrl_name(v))
        category = v.get_category(self.__pipeline)
        categories = v.get_category_choices(self.__pipeline)
        feature_name = v.get_feature_name(self.__pipeline)
        feature_names = v.get_feature_name_choices(self.__pipeline)
        image_name = v.get_image_name(self.__pipeline)
        image_names = v.get_image_name_choices(self.__pipeline)
        scale = v.get_scale(self.__pipeline)
        scales = v.get_scale_choices(self.__pipeline)
        def set_up_combobox(ctrl, text_ctrl, choices, value, always_show=False):
            if len(choices):
                if not (len(ctrl.Strings) == len(choices) and
                        all([x==y for x,y in zip(ctrl.Strings,choices)])):
                    ctrl.Clear()
                    ctrl.AppendItems(choices)
                if (not value is None) and ctrl.Value != value:
                    ctrl.Value = value
                ctrl.Show()
                text_ctrl.Show()
            elif always_show:
                ctrl.Clear()
                ctrl.Value = "No measurements available"
            else:
                ctrl.Hide()
                text_ctrl.Hide()
        set_up_combobox(category_ctrl, category_text_ctrl, categories, 
                        category, True)
        set_up_combobox(feature_ctrl, feature_text_ctrl, 
                        feature_names, feature_name)
        set_up_combobox(image_ctrl, image_text_ctrl, image_names, image_name)
        set_up_combobox(scale_ctrl, scale_text_ctrl, scales, scale)
        return panel
    
    def add_listener(self,listener):
        self.__listeners.append(listener)
    
    def remove_listener(self,listener):
        self.__listeners.remove(listener)
    
    def notify(self,event):
        for listener in self.__listeners:
            listener(self,event)
            
    def __on_column_sized(self,event):
        self.__module_panel.GetTopLevelParent().Layout()
    
    def __on_checkbox_change(self,event,setting,control):
        self.__on_cell_change(event, setting, control)
        self.reset_view()
    
    def __on_combobox_change(self,event,setting,control):
        self.__on_cell_change(event, setting, control)
        self.reset_view()
        
    def __on_cell_change(self,event,setting,control):
        old_value = str(setting)
        if isinstance(control,wx.CheckBox):
            proposed_value = (control.GetValue() and 'Yes') or 'No'
        else:
            proposed_value = str(control.GetValue())
        setting_edited_event = SettingEditedEvent(setting,proposed_value,event)
        self.notify(setting_edited_event)
    
    def __on_min_change(self,event,setting,control):
        old_value = str(setting)
        proposed_value="%s,%s"%(str(control.Value),str(setting.max))
        setting_edited_event = SettingEditedEvent(setting,proposed_value,event)
        self.notify(setting_edited_event)
        
    def __on_max_change(self,event,setting,control):
        old_value = str(setting)
        proposed_value="%s,%s"%(str(setting.min),str(control.Value))
        setting_edited_event = SettingEditedEvent(setting,proposed_value,event)
        self.notify(setting_edited_event)
        
    def __on_pipeline_event(self,pipeline,event):
        if (isinstance(event,cellprofiler.pipeline.PipelineLoadedEvent) or
            isinstance(event,cellprofiler.pipeline.PipelineClearedEvent)):
            self.clear_selection()
    
    def __on_do_something(self, event, setting):
        setting.on_event_fired()
        self.reset_view()
    
    def on_idle(self,event):
        """Check to see if the selected module is valid"""
        if self.__module:
            validation_error = None
            try:
                self.__module.test_valid(self.__pipeline)
            except cellprofiler.settings.ValidationError, instance:
                validation_error = instance
            for idx, setting in zip(range(len(self.__module.visible_settings())),self.__module.visible_settings()):
                try:
                    if validation_error and validation_error.setting.key() == setting.key():
                        raise validation_error
                    setting.test_valid(self.__pipeline)
                    if self.__static_texts[idx].GetForegroundColour() == ERROR_COLOR:
                        self.__controls[idx].SetToolTipString('')
                        for child in self.__controls[idx].GetChildren():
                            child.SetToolTipString('')
                        self.__static_texts[idx].SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
                        self.__static_texts[idx].Refresh()
                except cellprofiler.settings.ValidationError, instance:
                    if self.__static_texts[idx].GetForegroundColour() != ERROR_COLOR:
                        self.__controls[idx].SetToolTipString(instance.message)
                        for child in self.__controls[idx].GetChildren():
                            child.SetToolTipString(instance.message)
                        self.__static_texts[idx].SetForegroundColour(ERROR_COLOR)
                        self.__static_texts[idx].Refresh()
    
    def reset_view(self):
        """Redo all of the controls after something has changed
        
        TO_DO: optimize this so that only things that have changed IRL change in the GUI
        """
        focus_control = wx.Window.FindFocus()
        if not focus_control is None:
            focus_name = focus_control.GetName()
        else:
            focus_name = None
        self.set_selection(self.__module.module_num)
        if focus_name:
            focus_control = self.module_panel.FindWindowByName(focus_name)
            if focus_control:
                focus_control.SetFocus()
        
class ModuleSizer(wx.PySizer):
    """The module sizer uses the maximum best width of the setting edit controls
    to compute the column widths, then it sets the text controls to wrap within
    the remaining space, then it uses the best height of each text control to lay
    out the rows.
    """
    
    def __init__(self,rows,cols=2):
        wx.PySizer.__init__(self)
        self.__rows = rows
        self.__cols = cols
        self.__min_text_width = 150
    
    def Reset(self, rows, cols=2, destroy_windows=True):
        if destroy_windows:
            windows = []
            for j in range(self.__rows):
                for i in range(self.__cols):
                    item = self.GetItem(self.idx(i,j))
                    if item is None:
                        print "Missing item"
                    if item.IsWindow():
                        window = item.GetWindow()
                        if isinstance(window, wx.Window):
                            windows.append(window)
            for window in windows:
                window.Hide()
                window.Destroy()
        self.Clear(False)    
        self.__rows = rows
        self.__cols = cols
    
    def CalcMin(self):
        """Calculate the minimum from the edit controls
        """
        if self.__rows * self.__cols == 0:
            return wx.Size(0,0)
        size = self.calc_edit_size()
        height = 0
        for j in range(0,self.__rows):
            row_height = 0
            for i in range(0,self.__cols):
                item = self.GetItem(self.idx(i,j))
                row_height = max([row_height,item.CalcMin()[1]])
            height += row_height;
        return wx.Size(size[0]+self.__min_text_width,height)
        
    def calc_edit_size(self):
        height = 0
        width  = 0
        for i in range(0,self.__rows):
            if len(self.Children) <= self.idx(1,i):
                break
            item = self.GetItem(self.idx(1,i))
            size = item.CalcMin()
            height += size[1]
            width = max(width,size[0])
        return wx.Size(width,height)
    
    def calc_max_text_width(self):
        width = self.__min_text_width
        for i in range(0,self.__rows):
            if len(self.Children) <= self.idx(0,i):
                break
            item = self.GetItem(self.idx(0,i))
            control = item.GetWindow()
            assert isinstance(control,wx.StaticText), 'Control at column 0, %d of grid is not StaticText: %s'%(i,str(control))
            text = control.GetLabel()
            text = text.replace('\n',' ')
            ctrl_width = control.GetTextExtent(text)[0]
            ctrl_width += 2* item.GetBorder()
            width = max(width, ctrl_width)
        return width
    
    def RecalcSizes(self):
        """Recalculate the sizes of our items, resizing the text boxes as we go  
        """
        if self.__rows * self.__cols == 0:
            return
        size = self.GetSize()
        width = size[0]-20
        edit_size = self.calc_edit_size()
        edit_width = edit_size[0] # the width of the edit controls portion
        max_text_width = self.calc_max_text_width()
        if edit_width + max_text_width < width:
            edit_width = width - max_text_width
        elif edit_width * 4 < width:
            edit_width = width/4
        text_width = max([width-edit_width,self.__min_text_width])
        #
        # Change all static text controls to wrap at the text width. Then
        # ask the items how high they are and do the layout of the line.
        #
        height = 0
        widths = [text_width, edit_width]
        panel = self.GetContainingWindow()
        for i in range(0,self.__rows):
            text_item = self.GetItem(self.idx(0,i))
            edit_item = self.GetItem(self.idx(1,i))
            inner_text_width = text_width - 2*text_item.GetBorder() 
            items = [text_item, edit_item]
            control = text_item.GetWindow()
            assert isinstance(control,wx.StaticText), 'Control at column 0, %d of grid is not StaticText: %s'%(i,str(control))
            text = control.GetLabel()
            if (text_width > self.__min_text_width and
                (text.find('\n') != -1 or
                 control.GetTextExtent(text)[0] > inner_text_width)):
                text = text.replace('\n',' ')
                control.SetLabel(text)
                control.Wrap(inner_text_width)
            item_heights = [text_item.CalcMin()[1],edit_item.CalcMin()[1]]
            for j in range(0,self.__cols):
                item_size = wx.Size(widths[j],item_heights[j])
                item_location = wx.Point(sum(widths[0:j]),height)
                item_location = panel.CalcScrolledPosition(item_location)
                items[j].SetDimension(item_location, item_size)
            height += max(item_heights)
        panel.SetVirtualSizeWH(width,height+20)

    def coords(self,idx):
        """Return the column/row coordinates of an indexed item
        
        """
        (col,row) = divmod(idx,self.__cols)
        return (col,row)

    def idx(self,col,row):
        """Return the index of the given grid cell
        
        """
        return row*self.__cols + col
