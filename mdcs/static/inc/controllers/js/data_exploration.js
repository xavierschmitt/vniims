loadTemplateSelectionControllers = function()
{
    console.log('BEGIN [loadTemplateSelectionControllers]');
    $('.btn.set-explore-template').on('click', setExploreCurrentTemplate);
    console.log('END [loadTemplateSelectionControllers]');
}

setExploreCurrentTemplate = function()
{
    var templateName = $(this).parent().parent().children(':first').text();
    var templateID = $(this).parent().parent().children(':first').attr('templateID');
    var templateFilename = $(this).parent().parent().children(':nth-child(2)').text();
    var tdElement = $(this).parent();
		
    tdElement.html('<img src="/static/resources/img/ajax-loader.gif" alt="Loading..."/>');
    $('.btn.set-template').off('click');
    
    console.log('[setExploreCurrentTemplate] Setting '+templateName+' with filename '+templateFilename+' as current template...');

    Dajaxice.explore.setCurrentTemplate(setCurrentTemplateCallback,{'templateFilename':templateFilename, 'templateID':templateID});

    return false;
}

setCurrentTemplateCallback = function(data)
{
    Dajax.process(data);
    console.log('BEGIN [setCurrentTemplateCallback]');
    console.log('data passed back to callback function: ' + data);

    $('#template_selection').load(document.URL +  ' #template_selection', function() {
		loadTemplateSelectionControllers();
		displayTemplateSelectedDialog();
    });
    console.log('END [setCurrentTemplateCallback]');
}


function makeInputsDroppable(){
	$( "#queryForm input[droppable=true]" ).droppable({
		hoverClass: "ui-state-hover",
		drop: function( event, ui ) {
			$(this).val(ui.draggable.text());
			updateUserInputs(ui.draggable.attr('id'),$(this).parent().attr('id')); 
		}
	});
}

function updateUserInputs(fromElementID, toCriteriaID){
	$("input").each(function(){
	    $(this).attr("value", $(this).val());
	});
	$('select option').each(function(){ this.defaultSelected = this.selected; });
	var html = $("#queryForm").html()
	Dajaxice.explore.updateUserInputs(Dajax.process,{'htmlForm':html, 'fromElementID':fromElementID, 'toCriteriaID':toCriteriaID});
}


function query(){
	$("input").each(function(){
	    $(this).attr("value", $(this).val());
	});
	$('select option').each(function(){ this.defaultSelected = this.selected; });
	var queryForm = $("#queryForm").html()
	var queryBuilder = $("#queryBuilder").html()
	
	Dajaxice.explore.executeQuery(Dajax.process,{'queryForm':queryForm, 'queryBuilder':queryBuilder});
}

resultsCallback = function()
{
	console.log('BEGIN [saveCustomXMLData]');

    window.location = "/explore/results"
    	
    console.log('END [saveCustomXMLData]');
}

function addField(){
	$("input").each(function(){
	    $(this).attr("value", $(this).val());
	});
	$('select option').each(function(){ this.defaultSelected = this.selected; });
	var html = $("#queryForm").html()
	Dajaxice.explore.addField(Dajax.process,{'htmlForm':html});
}

function removeField(tagID){
	$("input").each(function(){
	    $(this).attr("value", $(this).val());
	});
	$('select option').each(function(){ this.defaultSelected = this.selected; });
	var queryForm = $("#queryForm").html()
	Dajaxice.explore.removeField(Dajax.process,{'queryForm':queryForm, 'criteriaID':tagID});
}

function saveQuery(){
	$("input").each(function(){
	    $(this).attr("value", $(this).val());
	});
	$('select option').each(function(){ this.defaultSelected = this.selected; });
	var queryForm = $("#queryForm").html()
	var queriesTable = $("#queriesTable").html()	
	Dajaxice.explore.saveQuery(Dajax.process,{'queryForm':queryForm, 'queriesTable':queriesTable});
}


function addSavedQueryToForm(savedQueryID){
	$("input").each(function(){
	    $(this).attr("value", $(this).val());
	});
	$('select option').each(function(){ this.defaultSelected = this.selected; });
	var queryForm = $("#queryForm").html()
	Dajaxice.explore.addSavedQueryToForm(Dajax.process,{'queryForm':queryForm, 'savedQueryID':savedQueryID})
} 

function deleteQuery(savedQueryID){
	var queriesTable = $("#queriesTable").html()
	Dajaxice.explore.deleteQuery(Dajax.process,{'queriesTable':queriesTable, 'savedQueryID':savedQueryID})
}

function clearCriterias(){
	$("input").each(function(){
	    $(this).attr("value", $(this).val());
	});
	$('select option').each(function(){ this.defaultSelected = this.selected; });
	var queryForm = $("#queryForm").html()
	Dajaxice.explore.clearCriterias(Dajax.process, {'queryForm':queryForm})
}


function clearQueries(){
	$("input").each(function(){
	    $(this).attr("value", $(this).val());
	});
	$('select option').each(function(){ this.defaultSelected = this.selected; });
	var queriesTable = $("#queriesTable").html()
	Dajaxice.explore.clearQueries(Dajax.process, {'queriesTable':queriesTable})
}

exploreData = function()
{
    console.log('BEGIN [exploreData]');


    // Need to Set input values explicitiy before sending innerHTML for save
    var elems = document.getElementsByName("xsdForm")[0].getElementsByTagName("input");
    for(var i = 0; i < elems.length; i++) {
	// sent attribute to property value
    	elems[i].setAttribute("value", elems[i].checked);
    	if(elems[i].checked == true)
    	{
    		elems[i].setAttribute("checked","checked");
    	}
    }
    $('select option').each(function(){ this.defaultSelected = this.selected; }); 
    Dajaxice.explore.saveCustomData(saveCustomXMLDataCallback,{'formContent':document.getElementById('xsdForm').innerHTML});

    console.log('END [exploreData]');
}

saveCustomXMLDataCallback = function()
{
    console.log('BEGIN [saveCustomXMLData]');

    window.location = "/explore/perform-search"
    	
    console.log('END [saveCustomXMLData]');
}


changeChoice = function(selectObj)
{
    console.log('BEGIN [changeChoice(' + selectObj + ')]');

    // get the index of the selected option 
    var idx = selectObj.selectedIndex;  

    for (i=0; i < selectObj.options.length;i++) {
    	if (i == idx){
    		$("#" + selectObj.id + "-" + i).removeAttr("style");
		} else {
			$("#" + selectObj.id + "-" + i).attr("style","display:none");
		}
    	
    }

    console.log('END [changeChoice(' + selectObj + ')]');
}

loadExploreCurrentTemplateForm = function()
{
    console.log('BEGIN [loadExploreCurrentTemplateForm]');

    $('.btn.clear-fields').on('click', clearFields);

    Dajaxice.explore.generateXSDTreeForQueryingData(Dajax.process); //,{'templateFilename':'xxxx'});

    console.log('END [loadExploreCurrentTemplateForm]');
}

clearFields = function()
{
    console.log('BEGIN [clearFields]');

    $('#dataQueryForm').find("select").val(0);
    $("#dataQueryForm").find("input").each(function() {
    	$( this ).removeAttr('checked');
    });
    $(function() {
        $( "#dialog-cleared-message" ).dialog({
            modal: true,
            buttons: {
		Ok: function() {
                    $( this ).dialog( "close" );
                }
	    }
        });
    });
	
    console.log('END [clearFields]');
}


downloadResults = function()
{
	console.log('BEGIN [downloadResults]');
		
	Dajaxice.explore.downloadResults(Dajax.process);
	
	console.log('END [downloadResults]');
}

displayErrors = function()
{
	$(function() {
        $( "#dialog-errors-message" ).dialog({
            modal: true,
            buttons: {
		Ok: function() {
                    $( this ).dialog( "close" );
                }
	    }
        });
    });
}


backToQuery = function()
{
	console.log('BEGIN [backToQuery]');
	
	Dajaxice.explore.backToQuery(backToQueryCallback);
	
	console.log('END [backToQuery]');
}


backToQueryCallback = function()
{
    console.log('BEGIN [backToQueryCallback]');

    window.location = "/explore/perform-search"    	
   
    console.log('END [backToQueryCallback]');
}