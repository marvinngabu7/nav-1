<table width="100%" class="mainWindow">
<tr><td class="mainWindowHead">
<p><?php echo gettext('Public filter groups'); ?></p>
</td></tr>

<tr><td>
<?php
include("loginordie.php");
loginOrDie();

echo "<p>" . gettext("Here you can create and setup new public filter groups.");

echo '<p><a href="?subaction=ny">';
echo gettext("Add a new filter group") . "</a>";


session_set('lastaction', 'futstyr');
$brukernavn = session_get('bruker'); $uid = session_get('uid');





if (in_array(get_get('subaction'), array('ny', 'endre') )) {

	$descr = gettext("Description :");
	print '<a name="nygruppe"></a><div class="newelement">';
	

	if ($subaction == 'endre') {
		print '<h2>' . gettext("Rename filter group") . '</h2>';
	} else {
		print '<h2>' . gettext("Add a new filter group") . '</h2>';
	}

	
	echo '<form name="form1" method="post" action="index.php?action=futstyr&subaction=';
	if ($subaction == 'endre') echo "endret"; else echo "nygruppe";
	echo '">';
	
	if ($subaction == 'endre') {
		print '<input type="hidden" name="gid" value="' . get_get('gid') . '">';
		$old_values = $dbh->utstyrgruppeInfo( get_get('gid') );
	}

	echo '<table width="100%" border="0" cellspacing="0" cellpadding="3">
	    <tr>
	    	<td width="30%"><p>' . gettext("Name") . '</p></td>
	    	<td width="70%"><input name="navn" type="text" size="40" 
	value="';
	if (isset($old_values)) { echo $old_values[0]; }
	echo '"></select>
	        </td>
	   </tr>';
	
    if ($subaction != 'endre') {
        echo '<tr><td width="30%"><p>' . gettext("Based upon") . '</p></td>';
    	echo '<td width="70%">';
        
        $ilist = '<SELECT name="basertpaa">' . "\n";
        $ilist .= '<OPTION value="0">' . gettext("Empty filter group");

        $utstyrgrlist = $dbh->listUtstyr($uid, 1);
        if (count($utstyrgrlist) > 0) {
            foreach ($utstyrgrlist as $utstyrelement) {
                if ( $utstyrelement[4] ) {
                    $owner = "Min";
                } else {
                    $owner = "Arvet";
                }
        
                $ilist .= '<OPTION value="' . $utstyrelement[0] . '">' . 
                    $utstyrelement[1] . "  [" . $owner  . "]\n" ;
            }
        }
        $ilist .= '</SELECT>' . "\n";
	
        echo $ilist;
        
        echo '</select></td></tr>';
    }
	
	echo '<tr><td colspan="2"><textarea name="descr" cols="60" rows="4">';
	
	if ($subaction == 'endre') {
	    echo $old_values[1];
	} else  {
	    echo $descr;
	}
	
	echo '</textarea>  </td>
	   </tr>	
	    <tr><td>&nbsp;</td><td align="right"><input type="submit" name="Submit" value="';
	    
	if ($subaction == 'endre') {
	    echo gettext("Save changes"); 
	} else  {
	    echo gettext("Add a new filter group");
	}
	echo '"></td>
	    </tr>
	  </table>
	</form></div>';
	
}









if (isset($subaction) && $subaction == 'endret') {

	if (post_get('gid') > 0) { 

		$dbh->endreUtstyrgruppe(post_get('gid'), post_get('navn'), post_get('descr') );
		$dbh->nyLogghendelse($uid, 5, gettext("Renamed public filter group") . " (" . post_get('navn') . ")");		
		unset($navn);
		unset($descr);
		print "<p><font size=\"+3\">" . gettext("OK</font>, filter group is renamed.");

	} else {
		print "<p><font size=\"+3\">" . gettext("An error</font> occured, the name is <b>not</b> changed.");
	}

}

if (isset($subaction) && $subaction == 'slett') {

	if (get_get('gid') > 0) { 	
		$dbh->slettUtstyrgruppe(get_get('gid') );
		$dbh->nyLogghendelse($uid, 4, gettext("Public filter group removed") . " (id=" . get_get('gid') . ")");		

		print "<p><font size=\"+3\">" . gettext("OK</font>, filter group is removed from the database.");

	} else {
		print "<p><font size=\"+3\">" . gettext("An error occured</font>, the filter group is <b>not</b> removed.");
	}

  
}



if (isset($subaction) && $subaction == "nygruppe") {
	print "<h3>" . gettext("Registering new filter group...") . "</h3>";
  
	if ($navn == "") $navn = gettext("No name");
	if ($uid > 0) { 

		$matchid = $dbh->nyUtstyrgruppeAdm(post_get('navn'), post_get('descr') );
		$dbh->nyLogghendelse($uid, 6, gettext("New public filter group") . " (" . post_get('navn') . ")");		
		print "<p><font size=\"+3\">" . gettext("OK</font>, a new filter group is created.");
    
	} else {
		print "<p><font size=\"+3\">" . gettext("An error</font> occured, a new filter group is <b>not</b> added to the database.");
	}

}




if (session_get('admin') >= 100) {


$l = new Lister( 113,
		array(gettext('Name'), gettext('#periods'), gettext('#filters'), gettext('Options..') ),
		array(50,  15, 15, 20),
		array('left',  'right', 'right', 'right'),
		array(true, true, true, false),
		0
);


print "<h3>" . gettext("Public filter groups") . "</h3>";

if ( get_exist('sortid') )
	$l->setSort(get_get('sort'), get_get('sortid') );
$utst = $dbh->listUtstyrAdm($l->getSort() );

for ($i = 0; $i < sizeof($utst); $i++) {


  if ($utst[$i][2] > 0 ) 
    { $ap = $utst[$i][2]; }
  else 
    {
      $ap = "<img alt=\"Ingen\" src=\"icons/stop.gif\">";
    }
    
  if ($utst[$i][3] > 0 ) 
    { $af = $utst[$i][3]; }
  else 
    {
      $af = "<img alt=\"Ingen\" src=\"icons/stop.gif\">";
    }    

	if ($utst[$i][4] == 't' ) { 
		$valg = '<a href="index.php?action=utstyrgrp&gid=' . $utst[$i][0]. 
			'">' . '<img alt="Open" src="icons/open2.gif" border=0></a>&nbsp;' .
			'<a href="index.php?action=futstyr&subaction=endre&gid=' . 
			$utst[$i][0] . '#nygruppe">' .
			'<img alt="Edit" src="icons/edit.gif" border=0></a>&nbsp;' .
			'<a href="index.php?action=futstyr&subaction=slett&gid=' . 
			$utst[$i][0] . '">' .
			'<img alt="Delete" src="icons/delete.gif" border=0></a>';;
			
	} else {
		$valg = "&nbsp;";
    }

	$l->addElement( array("<p>" . $utst[$i][1],  // navn
		$ap, $af, // verdi
		$valg ) 
	);

	$inh = new HTMLCell("<p class=\"descr\">" . $utst[$i][5] . "</p>");	  
	$l->addElement (&$inh);
}

print $l->getHTML();

print "<p>[ <a href=\"index.php?action=" . best_get('action') . "\">" . gettext("update") . " <img src=\"icons/refresh.gif\" class=\"refresh\" alt=\"oppdater\" border=0> ]</a> ";
print gettext("Number of groups: ") . sizeof($utst);


}


?>
</td></tr>
</table>
