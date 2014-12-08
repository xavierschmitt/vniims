/**
 * 
 * File Name: xsd_mgr.js
 * Author: Sharief Youssef
 * 		   sharief.youssef@nist.gov
 *
 *        Guillaume SOUSA AMARAL
 *        guillaume.sousa@nist.gov
 * 
 * Sponsor: National Institute of Standards and Technology (NIST)
 * 
 */

/**
 * Load controllers for template/type upload management
 */
loadUploadManagerHandler = function()
{
    console.log('BEGIN [loadUploadManagerHandler]');
    $('.retrieve').on('click',restoreObject);
    $('.edit').on('click',editInformation);
    $('.version').on('click', manageVersions);    
    $('.delete').on('click', deleteObject);
    $('.upload').on('click', uploadObject);
    console.log('END [loadUploadManagerHandler]');
}

/**
 * Open a window for the version management
 */
manageVersions = function()
{
    var modelName = $(this).parent().siblings(':first').text();
    var modelFilename = $(this).parent().siblings(':nth-child(2)').text();
    var tdElement = $(this).parent();
    var objectID = $(this).attr("objectid");
    var objectType = $(this).attr("objectType");
    
   
	versionDialog = $('<div title="Manage Versions" id="dialog-manage-versions">'+
			'<iframe id="version-upload-frame" style="width:500px;height:auto; min-height:400px;" src="/admin/manage-versions?id='+ objectID +'&type='+ objectType +'">'+
			'</iframe>'+	
	  '</div>' ).dialog({
        modal: true,
        width:520,
        height:510,
        resizable:false,
        close: function(event, ui){
        	$(this).dialog('destroy').remove();
        	$('#model_selection').load(window.parent.document.URL +  ' #model_selection', function() {
        	      loadUploadManagerHandler();
        	});  
        },
        buttons: {
        	OK: function() {
        		$(this).dialog('close');
                $('#model_selection').load(document.URL +  ' #model_selection', function() {
                    loadUploadManagerHandler();
                }); 
            },
            Cancel: function() {
            	$(this).dialog('close');
                $('#model_selection').load(document.URL +  ' #model_selection', function() {
                    loadUploadManagerHandler();
                }); 
            }
    }
    });   
}

/**
 * Handler for the reading of version of a template
 * @param evt
 */
function handleSchemaVersionUpload(evt) {
	console.log("test")
	var files = evt.target.files; // FileList object
    reader = new FileReader();
    reader.onload = function(e){
    	Dajaxice.admin.setSchemaVersionContent(Dajax.process,{"versionContent":reader.result, "versionFilename":files[0].name});
    }
    reader.readAsText(files[0]);
  }

/**
 * Handler for the reading of version of a type
 * @param evt
 */
function handleTypeVersionUpload(evt) {
	var files = evt.target.files; // FileList object
    reader = new FileReader();
    reader.onload = function(e){
    	Dajaxice.admin.setTypeVersionContent(Dajax.process,{"versionContent":reader.result, "versionFilename":files[0].name});
    }
    reader.readAsText(files[0]);
  }

/**
 * Upload a version
 */
uploadVersion = function()
{
	var objectVersionID = $("#updateVersionBtn").attr("versionid");
	var objectType = $("#updateVersionBtn").attr("objectType");	
	
	Dajaxice.admin.uploadVersion(Dajax.process,{"objectVersionID":objectVersionID, "objectType": objectType})
}

/**
 * Display errors for upload
 */
showUploadErrorDialog = function()
{
	$(function() {
        $( "#dialog-upload-error" ).dialog({
            modal: true,
            buttons: {
            	Ok: function() {	
            		$( this ).dialog( "close" );
                }
            }
        });
    });
}

/**
 * Set the current version to be used on the user side
 * @param setCurrent
 */
setCurrentVersion = function(setCurrent)
{
	current = document.getElementById(setCurrent);
	var objectid = $(current).attr("objectid");
	var objectType = $(current).attr("objectType");
	
	Dajaxice.admin.setCurrentVersion(Dajax.process,{"objectid":objectid, "objectType":objectType});
}

/**
 * Delete a version
 * @param toDelete
 */
deleteVersion = function(toDelete)
{			
	current = document.getElementById(toDelete);
	var objectid = $(current).attr("objectid");
	var objectType = $(current).attr("objectType");
	Dajaxice.admin.assignDeleteCustomMessage(Dajax.process,{"objectid":objectid, "objectType":objectType});
	$(function() {
			$('#dialog-deleteversion-message').dialog({
	            modal: true,
	            buttons: {
	            	Yes: function() {	
						var newCurrent = ""
						try{
							var idx = $("#selectCurrentVersion")[0].selectedIndex
							newCurrent = $("#selectCurrentVersion")[0].options[idx].value
						}
						catch(e){}
						Dajaxice.admin.deleteVersion(Dajax.process,{"objectid":objectid, "objectType":objectType,"newCurrent":newCurrent});
	                    $( this ).dialog( "close" );
	                },
	                No: function() {
	                    $( this ).dialog( "close" );
	                }
		    }
	        });
	    });
}

/**
 * Restore a template or a type
 */
restoreObject = function()
{
    var objectID = $(this).attr("objectid");
    var objectType = $(this).attr("objectType");
    
    Dajaxice.admin.restoreObject(Dajax.process,{'objectid':objectID, 'objectType':objectType});
}

/**
 * Restore a version of a template or a type
 * @param toRestore
 */
restoreVersion = function(toRestore)
{
	current = document.getElementById(toRestore);
	var objectID = $(current).attr("objectid");
	var objectType = $(current).attr("objectType");
	
	Dajaxice.admin.restoreVersion(Dajax.process,{'objectid':objectID, 'objectType':objectType});
}

/**
 * Edit general information of a template or a type
 */
editInformation = function()
{
    var objectName = $(this).parent().siblings(':first').text();
    var objectFilename = $(this).parent().siblings(':nth-child(2)').text();
    var objectID = $(this).attr("objectid");
    var objectType = $(this).attr("objectType");
    
    $("#edit-name")[0].value = objectName;
    $("#edit-filename")[0].value = objectFilename;
    
	$(function() {
        $( "#dialog-edit-info" ).dialog({
            modal: true,
            buttons: {
            	Ok: function() {	
					var newName = $("#edit-name")[0].value;
					var newFilename = $("#edit-filename")[0].value;
					Dajaxice.admin.editInformation(Dajax.process,{'objectid':objectID, 'objectType':objectType, 'newName':newName,'newFilename':newFilename});
                },
                Cancel: function() {
                    $( this ).dialog( "close" );
                }
            }
        });
    });
}


/**
 * Delete a template or a type
 */
deleteObject = function()
{
    console.log('BEGIN [deleteObject]');
    var objectName = $(this).parent().siblings(':first').text();
    var objectFilename = $(this).parent().siblings(':nth-child(2)').text();
    var objectID = $(this).attr("objectid");
    var objectType = $(this).attr("objectType");

    document.getElementById("object-to-delete").innerHTML = objectName;

    $(function() {
        $( "#dialog-deleteconfirm-message" ).dialog({
            modal: true,
            buttons: {
		Yes: function() {
                    deleteObjectConfirmed(objectID, objectType);
                    $( this ).dialog( "close" );
                },
		No: function() {
                    $( this ).dialog( "close" );
                }
	    }
        });
    });
	
    console.log('END [deleteObject]');
}

/**
 * Display a message when the delete is confirmed
 */
deleteObjectConfirmed = function(objectID, objectType)
{
    console.log('BEGIN [deleteObjectConfirmed('+objectID+')]');

    Dajaxice.admin.deleteObject(deleteObjectCallback,{'objectID':objectID, "objectType":objectType});

    console.log('END [deleteObjectConfirmed('+objectID+')]');
}

/**
 * Update the display when an object is deleted
 */
deleteObjectCallback = function(data)
{
    console.log('BEGIN [deleteObjectCallback]');

    Dajax.process(data);

    $('#model_selection').load(document.URL +  ' #model_selection', function() {
	loadUploadManagerHandler();
    });

    console.log('END [deleteObjectCallback]');
}


/**
 * Upload a template or a type
 */
uploadObject = function()
{
    console.log('BEGIN [uploadObject]');

    document.getElementById('object_name').value = ""
    document.getElementById('files').value = ""
    document.getElementById('list').innerHTML = ""
    document.getElementById('objectNameErrorMessage').innerHTML = ""

    $(function() {
        $( "#dialog-upload-message" ).dialog({
            modal: true,
            buttons: {
		Ok: function() {
                    $( this ).dialog( "close" );
                },
		Cancel: function() {
                    $( this ).dialog( "close" );
                }
	    }
        });
    });
	
    console.log('END [uploadObject]');
}

/**
 * Display error message when bad edition of type
 */
showErrorEditType = function(){
	$(function() {
        $( "#dialog-error-edit" ).dialog({
            modal: true,
            buttons: {
			Ok: function() {
                $( this ).dialog( "close" );
	          },
		    }
        });
    });
}
